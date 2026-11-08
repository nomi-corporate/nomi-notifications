using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Npgsql;

namespace Nomi.Notifications.Infrastructure.Persistence;

internal sealed class NotificationsDatabaseHealthCheck(NotificationsDbContext database) : IHealthCheck
{
    public async Task<HealthCheckResult> CheckHealthAsync(
        HealthCheckContext context,
        CancellationToken cancellationToken = default)
    {
        try
        {
            await database.Database.OpenConnectionAsync(cancellationToken);
            await database.Database.ExecuteSqlRawAsync("SELECT 1", cancellationToken);
            await database.Database.CloseConnectionAsync();
            return HealthCheckResult.Healthy();
        }
        catch (PostgresException error)
        {
            // SQLSTATE identifies the failure without logging credentials or server messages.
            return HealthCheckResult.Unhealthy(
                $"Notifications database is unavailable (SQLSTATE {error.SqlState}).");
        }
        catch (NpgsqlException)
        {
            return HealthCheckResult.Unhealthy(
                "Notifications database connection failed. Check network and TLS configuration.");
        }
        catch (ArgumentException)
        {
            return HealthCheckResult.Unhealthy("Notifications database configuration is invalid.");
        }
    }
}
