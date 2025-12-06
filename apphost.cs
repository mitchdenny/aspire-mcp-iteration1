#:sdk Aspire.AppHost.Sdk@13.1.0-pr.13343.g580cd576
#:package Aspire.Hosting.JavaScript@13.1.0-pr.13343.g580cd576
#:package Aspire.Hosting.Python@13.1.0-pr.13343.g580cd576
#:package Aspire.Hosting.Redis@13.1.0-pr.13343.g580cd576
#:package Aspire.Hosting.PostgreSQL@13.1.0-pr.13343.g580cd576

var builder = DistributedApplication.CreateBuilder(args);

var cache = builder.AddRedis("cache");

// PostgreSQL with weather database
var postgres = builder.AddPostgres("postgres")
    .WithPgAdmin()
    .WithBindMount("./db", "/docker-entrypoint-initdb.d", isReadOnly: true);

var weatherDb = postgres.AddDatabase("weatherdb");

var app = builder.AddUvicornApp("app", "./app", "main:app")
    .WithUv()
    .WithExternalHttpEndpoints()
    .WithReference(cache)
    .WaitFor(cache)
    .WithReference(weatherDb)
    .WaitFor(weatherDb)
    .WithHttpHealthCheck("/health");

// Weather sync service
var weatherSync = builder.AddUvicornApp("weather-sync", "./weather-sync", "main:app")
    .WithUv()
    .WithReference(weatherDb)
    .WaitFor(weatherDb);

var frontend = builder.AddViteApp("frontend", "./frontend")
    .WithReference(app)
    .WaitFor(app);

app.PublishWithContainerFiles(frontend, "./static");

builder.Build().Run();
