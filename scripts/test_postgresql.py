"""Integration checks against disposable Docker resources, never an AWS database."""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import uuid

SERVICE = "notifications"
TITLE = "Notifications"
ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18-alpine@sha256:10a5c69a83035ab5239f5620d708520e8b28f5aa1f2b20143e6024532edadfb5"
DATABASE = "nomi_" + SERVICE
APP = DATABASE + "_app"
MIGRATOR = DATABASE + "_migrator"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", help="Existing local service image; otherwise builds an isolated one.")
    args = parser.parse_args()
    docker = shutil.which("docker")
    if not docker and os.name == "nt":
        candidate = Path(os.environ.get("LOCALAPPDATA", "")) / "Programs/DockerDesktop/resources/bin/docker.exe"
        if candidate.is_file():
            docker = str(candidate)
    if not docker:
        raise SystemExit("Docker não encontrado. Inicie o Docker Desktop/Engine.")
    prefix = "nomi-" + SERVICE + "-check-" + uuid.uuid4().hex[:10]
    network = prefix + "-network"
    volume = prefix + "-data"
    pg = prefix + "-postgres"
    image = args.image or prefix + ":test"
    resources = []
    network_created = volume_created = image_created = False
    db_password = secrets.token_hex(32)
    app_password = secrets.token_hex(32)
    migrator_password = secrets.token_hex(32)

    def command(argv, *, input=None, env=None, check=True, timeout=120):
        result = subprocess.run(argv, input=input, text=True, encoding="utf-8", errors="replace",
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                cwd=ROOT, env=env, timeout=timeout)
        if check and result.returncode:
            safe = result.stderr + result.stdout
            for value in (db_password, app_password, migrator_password):
                safe = safe.replace(value, "[REDACTED]")
            raise RuntimeError(safe[-6000:])
        return result

    def dc(*argv, **kwargs):
        return command([docker, *argv], **kwargs)

    with tempfile.TemporaryDirectory(prefix=prefix) as directory:
        directory = Path(directory)

        def env_file(name, values):
            path = directory / (name + ".env")
            path.write_text("".join(f"{key}={value}\n" for key, value in values.items()), encoding="utf-8")
            path.chmod(0o600)
            return str(path)

        pg_env = env_file("postgres", {"POSTGRES_PASSWORD": db_password})
        role_env = {
            APP: env_file("app", {"PGPASSWORD": app_password}),
            MIGRATOR: env_file("migrator", {"PGPASSWORD": migrator_password}),
        }

        def sql(query, role="postgres", database=DATABASE, denied=False):
            arguments = ["exec", "-i"]
            if role != "postgres":
                arguments += ["--env-file", role_env[role]]
            arguments += [pg, "psql", "-X", "-q", "-t", "-A", "-w", "-U", role,
                          "-d", database, "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=sqlstate"]
            if role != "postgres":
                arguments += ["-h", "127.0.0.1"]
            result = dc(*arguments, input=query, check=not denied)
            if denied:
                assert result.returncode != 0 and "42501" in result.stderr, "Expected permission denied (42501)."
            return result.stdout.strip()

        def start_api(suffix, connection=None):
            name = prefix + "-" + suffix
            arguments = ["run", "--detach", "--name", name, "--network", network,
                         "--publish", "127.0.0.1::8080", "--memory", "384m"]
            if connection is not None:
                path = env_file(suffix, {"ConnectionStrings__" + TITLE: connection})
                arguments += ["--env-file", path]
            dc(*arguments, image)
            resources.append(name)
            info = json.loads(dc("inspect", name).stdout)[0]
            port = info["NetworkSettings"]["Ports"]["8080/tcp"][0]["HostPort"]
            return name, "http://127.0.0.1:" + port

        def health(base, endpoint, status, attempts=30):
            for _ in range(attempts):
                try:
                    with urllib.request.urlopen(base + "/health/" + endpoint, timeout=8) as response:
                        code = response.status
                        body = response.read().decode()
                except urllib.error.HTTPError as error:
                    code = error.code
                    body = error.read().decode()
                except (OSError, TimeoutError):
                    time.sleep(0.5)
                    continue
                if code == status and body == ("Healthy" if status == 200 else "Unhealthy"):
                    return
                time.sleep(0.5)
            raise AssertionError(f"{endpoint} did not return {status}.")

        try:
            dc("info")
            if not args.image:
                dc("build", "--tag", image, ".", timeout=600)
                image_created = True
            dc("network", "create", network)
            network_created = True
            dc("volume", "create", volume)
            volume_created = True
            dc("run", "--detach", "--name", pg, "--network", network, "--network-alias", "database",
               "--env-file", pg_env, "--publish", "127.0.0.1::5432",
               "--mount", f"type=volume,src={volume},dst=/var/lib/postgresql", POSTGRES_IMAGE)
            resources.append(pg)
            for _ in range(90):
                # Require the final TCP server, not the temporary init server on the Unix socket.
                if dc("exec", pg, "pg_isready", "-h", "127.0.0.1", "-U", "postgres", check=False).returncode == 0:
                    break
                time.sleep(1)
            else:
                raise RuntimeError("PostgreSQL did not become ready.")
            sql(f"""
CREATE ROLE {MIGRATOR} LOGIN PASSWORD '{migrator_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE ROLE {APP} LOGIN PASSWORD '{app_password}' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
CREATE DATABASE {DATABASE};
REVOKE ALL ON DATABASE {DATABASE} FROM PUBLIC;
GRANT CONNECT ON DATABASE {DATABASE} TO {APP}, {MIGRATOR};
CREATE DATABASE nomi_peer;
REVOKE ALL ON DATABASE nomi_peer FROM PUBLIC;
REVOKE CONNECT ON DATABASE postgres, template1 FROM PUBLIC;
""", database="postgres")
            sql(f"""
REVOKE ALL ON SCHEMA public FROM PUBLIC;
CREATE SCHEMA {SERVICE} AUTHORIZATION {MIGRATOR};
CREATE SCHEMA migrations AUTHORIZATION {MIGRATOR};
GRANT USAGE ON SCHEMA {SERVICE} TO {APP};
ALTER DEFAULT PRIVILEGES FOR ROLE {MIGRATOR} IN SCHEMA {SERVICE}
 GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP};
ALTER DEFAULT PRIVILEGES FOR ROLE {MIGRATOR} IN SCHEMA {SERVICE}
 GRANT USAGE, SELECT ON SEQUENCES TO {APP};
""")
            assert sql("SELECT rolsuper OR rolcreatedb OR rolcreaterole FROM pg_roles WHERE rolname=current_user", APP) == "f"
            assert sql(f"SELECT pg_has_role(current_user, '{MIGRATOR}', 'MEMBER')", APP) == "f"
            assert sql("SELECT has_schema_privilege('migrations', 'USAGE')", APP) == "f"
            assert sql("SELECT has_database_privilege('nomi_peer','CONNECT')", APP) == "f"
            sql(f"CREATE TABLE {SERVICE}.probe (id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY, value text NOT NULL)", MIGRATOR)
            sql("CREATE TABLE migrations.probe (id integer PRIMARY KEY)", MIGRATOR)
            sql(f"CREATE TABLE {SERVICE}.denied (id integer)", APP, denied=True)
            sql("SELECT * FROM migrations.probe", APP, denied=True)
            sql(f"INSERT INTO {SERVICE}.probe(value) VALUES ('before_restart')", APP)
            sql(f"UPDATE {SERVICE}.probe SET value='persisted'", APP)
            assert sql(f"SELECT value FROM {SERVICE}.probe", APP) == "persisted"
            print("Permissões e CRUD: app sem administração, DDL, migrations ou acesso ao banco vizinho.")

            info = json.loads(dc("inspect", pg).stdout)[0]
            pg_port = info["NetworkSettings"]["Ports"]["5432/tcp"][0]["HostPort"]
            migration_env = os.environ.copy()
            migration_env["NOMI_" + SERVICE.upper() + "_MIGRATION_CONNECTION"] = (
                f"Host=127.0.0.1;Port={pg_port};Database={DATABASE};Username={MIGRATOR};Password={migrator_password};Timeout=3")
            command(["dotnet", "tool", "restore"], timeout=180)
            command(["dotnet", "ef", "dbcontext", "info", "--project", f"src/Nomi.{TITLE}.Infrastructure",
                     "--startup-project", f"src/Nomi.{TITLE}.Api"], env=migration_env, timeout=180)
            print("Ferramenta de migrations: contexto construído com identidade separada.")

            connection = f"Host=database;Database={DATABASE};Username={APP};Password={app_password};Timeout=2;Command Timeout=3"
            _, missing = start_api("missing")
            health(missing, "live", 200)
            health(missing, "ready", 503)
            bad_name, bad = start_api("bad-password", connection.replace(app_password, "intentionally-invalid"))
            health(bad, "live", 200)
            health(bad, "ready", 503)
            bad_logs = dc("logs", bad_name)
            logs = bad_logs.stdout + bad_logs.stderr
            assert "SQLSTATE 28P01" in logs, "Authentication failure should expose only SQLSTATE in logs."
            assert app_password not in logs and "intentionally-invalid" not in logs, "Password leaked into logs."
            _, wrong = start_api("wrong-database", connection.replace(f"Database={DATABASE};", "Database=nomi_peer;"))
            health(wrong, "ready", 503)
            good_name, good = start_api("connected", connection)
            health(good, "live", 200)
            health(good, "ready", 200)
            assert sql(f"SELECT count(*) FROM information_schema.tables WHERE table_schema IN ('{SERVICE}', 'migrations')") == "2", "Startup created unexpected tables."
            print("Readiness: 200 com PostgreSQL; 503 sem configuração, senha inválida ou banco não autorizado.")
            # Release memory before testing the connection recovery scenario.
            for name in resources[:]:
                if name not in (pg, good_name):
                    dc("rm", "--force", name)
                    resources.remove(name)
            dc("stop", "--time", "5", pg)
            health(good, "live", 200)
            health(good, "ready", 503)
            dc("start", pg)
            health(good, "ready", 200)
            assert sql(f"SELECT value FROM {SERVICE}.probe", APP) == "persisted"
            sql(f"DELETE FROM {SERVICE}.probe", APP)
            assert sql(f"SELECT count(*) FROM {SERVICE}.probe", APP) == "0"
            print("Banco parado: live 200 / ready 503. Após reinício: ready 200 e dados preservados.")
            print("Validação concluída sem acessar a AWS nem criar tabelas de negócio.")
        finally:
            for name in reversed(resources):
                dc("rm", "--force", name, check=False)
            if volume_created:
                dc("volume", "rm", volume, check=False)
            if network_created:
                dc("network", "rm", network, check=False)
            if image_created:
                dc("image", "rm", image, check=False)


if __name__ == "__main__":
    main()
