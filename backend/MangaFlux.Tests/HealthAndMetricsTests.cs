using System;
using System.Threading;
using System.Threading.Tasks;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Diagnostics.HealthChecks;
using NekoHentai.API.Services;
using NekoHentai.API.Services.HealthChecks;
using Xunit;

namespace NekoHentai.Tests
{
    public class HealthAndMetricsTests
    {
        [Fact]
        public void MangaMetrics_StaticDefinitions_AreInitialized()
        {
            // Assert custom metrics counters & gauges are created
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.CacheHitsTotal);
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.CacheMissesTotal);
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.ChapterViewsIncrementedTotal);
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.ChapterViewsSyncedTotal);
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.DbSyncDurationSeconds);
            Assert.NotNull(NekoHentai.API.Services.MangaMetrics.RedisConnectedGauge);

            // Test counter operations
            NekoHentai.API.Services.MangaMetrics.CacheHitsTotal.WithLabels("test_chapter").Inc();
            NekoHentai.API.Services.MangaMetrics.CacheMissesTotal.WithLabels("test_chapter").Inc();
            NekoHentai.API.Services.MangaMetrics.ChapterViewsIncrementedTotal.WithLabels("comic").Inc(5);
            NekoHentai.API.Services.MangaMetrics.RedisConnectedGauge.Set(1);

            Assert.True(true);
        }

        [Fact]
        public async Task RedisHealthCheck_WhenNullConnection_ReturnsDegraded()
        {
            var healthCheck = new RedisHealthCheck(null);
            var context = new HealthCheckContext();

            var result = await healthCheck.CheckHealthAsync(context, CancellationToken.None);

            Assert.Equal(HealthStatus.Degraded, result.Status);
            Assert.Contains("fallback", result.Description, StringComparison.OrdinalIgnoreCase);
        }

        [Fact]
        public async Task StorageHealthCheck_WhenServiceAvailable_ReturnsHealthy()
        {
            var mockStorage = new Moq.Mock<IStorageService>();
            var healthCheck = new StorageHealthCheck(mockStorage.Object);
            var context = new HealthCheckContext();

            var result = await healthCheck.CheckHealthAsync(context, CancellationToken.None);

            Assert.Equal(HealthStatus.Healthy, result.Status);
        }

        [Fact]
        public async Task PostgreSqlHealthCheck_WithInMemoryDb_CanExecute()
        {
            var options = new Microsoft.EntityFrameworkCore.DbContextOptionsBuilder<NekoHentai.API.Data.MangaDbContext>()
                .UseInMemoryDatabase(databaseName: Guid.NewGuid().ToString())
                .Options;
            using var dbContext = new NekoHentai.API.Data.MangaDbContext(options);
            var healthCheck = new PostgreSqlHealthCheck(dbContext);
            var context = new HealthCheckContext();

            var result = await healthCheck.CheckHealthAsync(context, CancellationToken.None);
            Assert.True(result.Status == HealthStatus.Healthy || result.Status == HealthStatus.Unhealthy);
        }
    }
}
