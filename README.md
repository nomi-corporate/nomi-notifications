# Nomi Notifications

Agendamento, cancelamento e entrega de lembretes a partir de eventos. Deve tratar duplicação, novas tentativas e falhas definitivas.

## Stack acordada

C# e .NET.

Infraestrutura AWS; autenticação Amazon Cognito; arquivos no S3. Cada serviço é implantado independentemente e controla seus próprios dados.


## Executar localmente

Instale o SDK .NET 10 compatível com `global.json`.

```sh
dotnet restore Nomi.Notifications.sln
dotnet build Nomi.Notifications.sln
dotnet run --project src/Nomi.Notifications.Api
```

Liveness: `http://localhost:5103/health/live` confirma somente que o processo responde. Readiness em `/health/ready` retorna 200 quando o PostgreSQL está acessível e 503 sem configuração ou quando a conexão falha. Consulte [PostgreSQL e execução na AWS](docs/postgresql.md).

## Estrutura

- `src/Nomi.Notifications.Api`: HTTP e composição das dependências.
- `src/Nomi.Notifications.Application`: casos de uso e portas de integração.
- `src/Nomi.Notifications.Domain`: regras e modelos de domínio.
- `src/Nomi.Notifications.Infrastructure`: adapters de persistência e provedores externos.

A conexão PostgreSQL, o contexto EF Core e a ferramenta de migrations estão preparados. Ainda não há entidades/tabelas de negócio, autenticação Cognito nem funcionalidades da TEC-003 implementadas. Sem conexão configurada, a API inicia com liveness saudável e readiness 503. Nenhuma migration é aplicada no startup.

## Contêiner

```sh
docker build -t nomi-notifications:dev .
docker run --rm -p 5103:8080 nomi-notifications:dev
```

CI verifica compilação, publicação, liveness e construção da imagem. Após os checks da master, o workflow publica uma imagem validada no ECR usando OIDC e registra seu digest. Configure as três variáveis descritas em [Entrega](docs/delivery.md). A implantação na EC2 ainda não está implementada.

## Documentação

- [PostgreSQL e execução na AWS](docs/postgresql.md)
- [Arquitetura](docs/architecture.md)
- [Entrega](docs/delivery.md)
- [Contribuição](CONTRIBUTING.md)
