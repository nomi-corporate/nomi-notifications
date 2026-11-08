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

Liveness: `http://localhost:5103/health/live`. O endpoint confirma somente que o processo responde; conexões de banco e filas ainda serão implementadas.

## Estrutura

- `src/Nomi.Notifications.Api`: HTTP e composição das dependências.
- `src/Nomi.Notifications.Application`: casos de uso e portas de integração.
- `src/Nomi.Notifications.Domain`: regras e modelos de domínio.
- `src/Nomi.Notifications.Infrastructure`: adapters de persistência e provedores externos.

Ainda não há endpoints acadêmicos, autenticação Cognito, banco configurado ou envio de notificações. A base executa sem credenciais AWS. As próximas entregas adicionam as funcionalidades da TEC-003.

## Contêiner

```sh
docker build -t nomi-notifications:dev .
docker run --rm -p 5103:8080 nomi-notifications:dev
```

CI verifica compilação, publicação, liveness e construção da imagem. Após os checks da master, o workflow publica uma imagem validada no ECR usando OIDC e registra seu digest. Configure as três variáveis descritas em [Entrega](docs/delivery.md). A implantação na EC2 ainda não está implementada.

## Documentação

- [Arquitetura](docs/architecture.md)
- [Entrega](docs/delivery.md)
- [Contribuição](CONTRIBUTING.md)
