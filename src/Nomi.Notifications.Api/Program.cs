using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Nomi.Notifications.Infrastructure;

var builder = WebApplication.CreateBuilder(args);
builder.Services.AddProblemDetails();
builder.Services.AddNotificationsPersistence(builder.Configuration);

var app = builder.Build();
app.UseExceptionHandler();
app.MapHealthChecks("/health/live", new HealthCheckOptions { Predicate = _ => false });
app.MapHealthChecks("/health/ready", new HealthCheckOptions
{
    Predicate = check => check.Tags.Contains("ready")
});
app.Run();

public partial class Program;
