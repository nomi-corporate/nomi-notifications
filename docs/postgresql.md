# PostgreSQL — Nomi Notifications

## Escopo

Base de conexão EF Core/PostgreSQL e readiness, como entrega parcial da TEC-005 e da TEC-007. Não cria entidades, tabelas de negócio, envio de notificações ou integração com IA. Não aplica `Migrate`/`EnsureCreated` no startup.

O serviço acessa somente `nomi_notifications`, com schema de aplicação `notifications` e histórico EF em `migrations.__EFMigrationsHistory`. No desenvolvimento AWS, Assistant e Notifications compartilham a instância RDS `nomi-dev-assistant`, mas usam bancos e identidades distintos. Não compartilhar connection strings nem consultar tabelas do outro serviço.

## Identidades e configuração

| Finalidade | Configuração | Usuário AWS de desenvolvimento |
| --- | --- | --- |
| Processo da API | `ConnectionStrings__Notifications` | `nomi_notifications_app` |
| Ferramenta de migrations | `NOMI_NOTIFICATIONS_MIGRATION_CONNECTION` | `nomi_notifications_migrator` |

Runtime: CONNECT no banco, USAGE em `notifications`, SELECT/INSERT/UPDATE/DELETE nas tabelas e USAGE/SELECT nas sequências. Não recebe DDL, administração, acesso ao schema `migrations` ou associação à role de migração. O migrador é proprietário dos dois schemas; deve executar as migrations com sua própria identidade para aplicar os privilégios padrão às tabelas novas.

Schemas e permissões AWS já foram configurados manualmente pelo responsável. Criar novos ambientes exige provisionar explicitamente esses recursos; o aplicativo não os cria. O script de integração cria sua própria infraestrutura Docker descartável e não deve ser adaptado para rodar sobre RDS.

## Endpoints

- `/health/live`: HTTP 200 `Healthy` quando o processo responde, mesmo sem banco.
- `/health/ready`: HTTP 200 `Healthy` quando abre uma conexão PostgreSQL e executa `SELECT 1`; HTTP 503 `Unhealthy` sem configuração, com senha inválida, banco não autorizado ou falha de rede/TLS.
- O corpo HTTP não contém diagnóstico ou credenciais. Falhas retornadas pelo PostgreSQL incluem apenas SQLSTATE no log; problemas de transporte usam mensagem genérica. Não habilitar sensitive data logging nem imprimir connection strings.
- Readiness de conexão não comprova existência/versão das tabelas, funcionamento de provedores, mensageria ou comportamento de negócio.

## Preparar a configuração na EC2

Pré-requisitos: Python 3, cliente `psql`, Docker, certificado RDS em `~/global-bundle.pem`, grupo do banco permitindo TCP 5432 a partir do grupo da EC2. O certificado deve ser legível pelo usuário não privilegiado do contêiner.

Com `scripts/configure_runtime.py` disponível no servidor, execute:

```bash
python3 scripts/configure_runtime.py --host ENDPOINT_DA_INSTANCIA_ASSISTANT
```

O script solicita a senha de `nomi_notifications_app` sem exibi-la, testa essa credencial com TLS `verify-full` antes de gravar e salva `~/nomi/env/notifications.env` com permissão 600. A pasta fica com permissão 700. Se a senha falhar, o arquivo anterior permanece. Para substituir uma configuração existente, acrescentar `--replace`.

O arquivo resultante contém a connection string Npgsql com `SSL Mode=VerifyFull`, certificado `/app/certs/global-bundle.pem`, GSS desabilitado, timeout de 10 segundos e pool limitado a 10 conexões. Não versionar nem enviar o arquivo em prints. A senha fica localmente em texto e deve evoluir para o mecanismo de segredos definido para o ambiente.

## Executar a imagem publicada

Obter o URI completo com `@sha256:...` do resumo/artefato `ecr-image.json` de uma execução bem-sucedida da master. Renovar o login ECR quando necessário. Não usar `latest` nem reconstruir a imagem no servidor.

```bash
export NOMI_IMAGE='URI_DO_ECR_COM_DIGEST'
docker pull "$NOMI_IMAGE"
```

Para a primeira execução (se já houver contêiner com esse nome, seguir o procedimento de atualização abaixo):

```bash
docker run -d \
  --name nomi-notifications \
  --restart unless-stopped \
  --memory 384m \
  --log-driver local \
  --log-opt max-size=10m \
  --log-opt max-file=3 \
  --publish 127.0.0.1:5103:8080 \
  --env-file "$HOME/nomi/env/notifications.env" \
  --mount "type=bind,src=$HOME/global-bundle.pem,dst=/app/certs/global-bundle.pem,readonly" \
  "$NOMI_IMAGE"
```

```bash
curl --fail --show-error --retry 10 --retry-delay 2 --retry-connrefused http://127.0.0.1:5103/health/live
curl --fail --show-error --retry 10 --retry-delay 2 --retry-connrefused http://127.0.0.1:5103/health/ready
```

Os dois devem retornar `Healthy`. O serviço permanece acessível somente na EC2 enquanto HTTPS e autenticação não forem implantados.

### Atualização manual e recuperação

1. Validar e salvar a configuração com o helper antes de interromper a API. Baixar a imagem nova por digest.
2. Registrar apenas o URI da imagem anterior com `docker inspect --format '{{.Config.Image}}' nomi-notifications`. Não imprimir `.Config.Env`, que contém segredos.
3. Interromper e renomear o contêiner existente para `nomi-notifications-previous`, verificando antes que esse nome não esteja ocupado. Criar o novo com o nome original e os parâmetros acima. Há uma breve indisponibilidade; este não é um rolling deploy.
4. Validar live e ready. Se falhar, remover apenas o novo contêiner, restaurar o nome do anterior e iniciá-lo. O contêiner antigo preserva suas próprias variáveis de ambiente; a versão antiga sem readiness terá somente liveness.
5. Após aceitação, remover o contêiner anterior de forma deliberada. Preservar no ECR o digest necessário para rollback.

Reiniciar um contêiner não recarrega `--env-file`; é necessário recriá-lo. Migrations futuras exigem plano de compatibilidade/rollback próprio. Não enviar a senha do migrador para o contêiner da aplicação.

## Ferramenta de migrations

Instalar/restaurar o SDK definido em `global.json`, executar `dotnet tool restore` e fornecer `NOMI_NOTIFICATIONS_MIGRATION_CONNECTION` por mecanismo local seguro. O valor deve usar a identidade de migração e TLS apropriado ao ambiente, sem ser versionado ou registrado no histórico de comandos.

```bash
dotnet ef dbcontext info --project src/Nomi.Notifications.Infrastructure --startup-project src/Nomi.Notifications.Api
dotnet ef migrations list --project src/Nomi.Notifications.Infrastructure --startup-project src/Nomi.Notifications.Api
```

O contexto está vazio: não criar uma migration vazia nem aplicar `database update` só para testar. Entidades, mapeamentos e migrations entram nas HUs correspondentes. O histórico fica no schema `migrations`, inacessível à aplicação.

## Verificação automatizada

```bash
python3 scripts/test_postgresql.py
```

Requer Docker Linux e SDK .NET. Constrói a imagem e usa PostgreSQL 18 com digest fixo, volume, rede e senhas aleatórias exclusivos da execução. Verifica CRUD, sequências, rejeição de DDL/administração/acesso ao banco vizinho, schema de migrations inacessível à aplicação, factory de design-time, falta de configuração, senha inválida, perda e recuperação de conexão e persistência após reinício. Não usa credenciais AWS. Os recursos de teste são removidos ao final, inclusive em falha; uma interrupção abrupta do processo pode exigir limpeza dos recursos identificados pelo prefixo `nomi-notifications-check-`.

O CI executa esse teste no job `Database integration`, exigido pela publicação no ECR. Isso valida PostgreSQL local em Docker; a validação TLS/RDS e readiness na EC2 só estará concluída após implantar e testar a nova imagem.
