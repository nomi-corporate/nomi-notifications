using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Nomi.Notifications.Infrastructure.Persistence;

public sealed class NotificationsDbContextFactory : IDesignTimeDbContextFactory<NotificationsDbContext>
{
    public NotificationsDbContext CreateDbContext(string[] args)
    {
        var connection = Environment.GetEnvironmentVariable("NOMI_NOTIFICATIONS_MIGRATION_CONNECTION");
        if (string.IsNullOrWhiteSpace(connection))
        {
            throw new InvalidOperationException(
                "Configure NOMI_NOTIFICATIONS_MIGRATION_CONNECTION com a identidade de migrations. " +
                "Consulte docs/postgresql.md para os comandos de migrations.");
        }

        var options = new DbContextOptionsBuilder<NotificationsDbContext>()
            .UseNpgsql(connection, provider =>
                provider.MigrationsHistoryTable("__EFMigrationsHistory", "migrations"))
            .Options;

        return new NotificationsDbContext(options);
    }
}
