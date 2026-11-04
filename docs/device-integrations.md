# Integrações de dispositivos

Notifications coordena planos, preferências e entrega. `INotificationDeliveryChannel` é uma porta da Application; adapters de provedores entram em Infrastructure e são registrados na composição da API.

Plataforma e provedor são dimensões distintas: Wear OS e um futuro watchOS podem exigir fluxos diferentes, e uma plataforma pode admitir mais de um provedor. A porta usa chaves internas extensíveis, sem pressupor que todo relógio receba push direto.

Nenhum adapter funcional foi registrado nesta base: não há envio real nem sucesso simulado. O adapter deverá traduzir resultados do fornecedor para aceitação, falha recuperável ou definitiva. Registrar aceitação pelo provedor não comprova leitura ou exibição.

Wear OS é o alvo atual. Para acrescentar Apple Watch, validar app watchOS, autenticação, capacidade de rede, espelhamento/entrega e orçamento. A enumeração HTTP `platform` da TEC-003 precisará evoluir de forma compatível antes de aceitar watchOS na API. Não criar um microsserviço por modelo de relógio.

A comunicação local entre celular e relógio pertence aos clientes. As APIs Academic e Assistant permanecem compartilhadas por clientes autorizados. Regras de confirmação, versão e idempotência valem para todas as plataformas.
