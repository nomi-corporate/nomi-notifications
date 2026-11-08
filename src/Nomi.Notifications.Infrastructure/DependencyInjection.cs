using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using Nomi.Notifications.Infrastructure.Persistence;

namespace Nomi.Notifications.Infrastructure;

public static class DependencyInjection
{
    public static IServiceCollection AddNotificationsPersistence(
        this IServiceCollection services,
        IConfiguration configuration)
    {
        var connection = configuration.GetConnectionString("Notifications");
        var healthChecks = services.AddHealthChecks();
        if (string.IsNullOrWhiteSpace(connection))
        {
            healthChecks.AddCheck("postgresql",
                () => HealthCheckResult.Unhealthy("Notifications database is not configured."),
                tags: ["ready"]);
            return services;
        }

        services.AddDbContext<NotificationsDbContext>(options => options.UseNpgsql(connection,
            provider => provider.MigrationsHistoryTable("__EFMigrationsHistory", "migrations")));
        healthChecks.AddCheck<NotificationsDatabaseHealthCheck>("postgresql", tags: ["ready"]);
        return services;
    }
}
