# Nomi Notifications

Agendamento, cancelamento e entrega de lembretes a partir de eventos. Deve tratar duplicação, novas tentativas e falhas definitivas.

## Stack acordada

C# e .NET.

Infraestrutura AWS; autenticação Amazon Cognito; arquivos no S3. Cada serviço é implantado independentemente e controla seus próprios dados.

## Estado inicial

Este repositório contém a documentação e os checks iniciais. O código da aplicação, o provisionamento AWS e o deploy ainda não foram implementados.

## Documentação

- [Arquitetura](docs/architecture.md)
- [CI/CD e proteção da master](docs/delivery.md)
- [Como contribuir](CONTRIBUTING.md)
