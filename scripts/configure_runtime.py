"""Run on EC2: verify the app credential before saving its Docker env file."""
import argparse
import getpass
import os
from pathlib import Path
import re
import subprocess
import tempfile

SERVICE = "notifications"
TITLE = "Notifications"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="RDS endpoint, without scheme or port.")
    parser.add_argument("--certificate", type=Path, default=Path.home() / "global-bundle.pem")
    parser.add_argument("--replace", action="store_true", help="Replace an existing configuration after validating the password.")
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9.-]+", args.host):
        parser.error("Informe somente o hostname do banco.")
    certificate = args.certificate.expanduser().resolve()
    if not certificate.is_file():
        parser.error("Certificado RDS não encontrado.")
    directory = Path.home() / "nomi/env"
    path = directory / (SERVICE + ".env")
    if path.exists() and not args.replace:
        parser.error("Arquivo existente preservado. Use --replace para atualizá-lo.")
    password = getpass.getpass(f"Senha de nomi_{SERVICE}_app: ")
    if not password or any(c in password for c in "\r\n\x00"):
        parser.error("Senha vazia ou com quebra de linha não é aceita.")
    env = os.environ.copy()
    env.update({
        "PGHOST": args.host, "PGPORT": "5432", "PGDATABASE": "nomi_" + SERVICE,
        "PGUSER": "nomi_" + SERVICE + "_app", "PGPASSWORD": password,
        "PGSSLMODE": "verify-full", "PGSSLROOTCERT": str(certificate),
        "PGCONNECT_TIMEOUT": "10", "PGPASSFILE": "/dev/null",
    })
    result = subprocess.run(["psql", "-X", "-w", "-q", "-t", "-A", "-c", "SELECT current_database(), current_user;"], env=env, timeout=20)
    if result.returncode:
        raise SystemExit("Conexão recusada. Nenhum arquivo de configuração foi alterado.")
    # Npgsql quoted values escape double quotes by doubling them.
    quoted_password = '"' + password.replace('"', '""') + '"'
    connection = (
        f"Host={args.host};Port=5432;Database=nomi_{SERVICE};Username=nomi_{SERVICE}_app;"
        f"Password={quoted_password};SSL Mode=VerifyFull;Root Certificate=/app/certs/global-bundle.pem;"
        "GSS Encryption Mode=Disable;Timeout=10;Maximum Pool Size=10"
    )
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    directory.chmod(0o700)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=directory, delete=False) as stream:
            temporary = Path(stream.name)
            temporary.chmod(0o600)
            stream.write(f"ConnectionStrings__{TITLE}={connection}\n")
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    print(f"Conexão validada. Configuração salva em {path}, com permissão 600.")
    print("Recrie o contêiner para carregar o arquivo; reiniciar não atualiza as variáveis.")


if __name__ == "__main__":
    main()
