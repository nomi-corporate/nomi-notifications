namespace Nomi.Notifications.Application.Delivery;

/// <summary>Porta implementada por adapters de provedores de entrega.</summary>
public interface INotificationDeliveryChannel
{
    string ProviderKey { get; }
    Task<DeliveryResult> SendAsync(NotificationEnvelope notification, DeviceDestination destination, CancellationToken cancellationToken);
}

public sealed record NotificationEnvelope(Guid NotificationId, string Title, string Body, DateTimeOffset ExpiresAt);

// PlatformKey identifica a plataforma; ProviderKey seleciona o adapter de entrega.
// Tokens pertencem à infraestrutura e nunca devem aparecer em logs.
public sealed record DeviceDestination(string PlatformKey, string ProviderKey, string PushToken);

public sealed record DeliveryResult(DeliveryOutcome Outcome, string? ProviderMessageId = null, string? ErrorCode = null);

public enum DeliveryOutcome
{
    AcceptedByProvider,
    RetryableFailure,
    PermanentFailure
}
