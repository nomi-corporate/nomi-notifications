# Arquitetura

## Responsabilidade

Agendamento, cancelamento e entrega de lembretes a partir de eventos. Deve tratar duplicação, novas tentativas e falhas definitivas.

## Limites

SOLID, casos de uso e adaptadores nas fronteiras externas. Organizar por funcionalidade. Cada serviço controla seus dados; comunicação por APIs e eventos versionados. Não compartilhar entidades de domínio nem consultar tabelas de outro serviço.

O Academic deve usar Transactional Outbox para publicar eventos associados a alterações persistidas. Consumidores devem processar eventos de forma idempotente.

## Decisões pendentes

- Provedor de IA e transcrição.
- Protocolo e suporte real do RM22/Micro OS 10; não há promessa de app instalável.
- Serviços AWS de execução, mensageria, região e orçamento.
- Contratos HTTP e eventos e sua estratégia de versionamento.

## Design

https://www.figma.com/design/VdmGhvLilFgMFDro8qt3GM?node-id=7-6
