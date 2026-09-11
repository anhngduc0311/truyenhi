using Prometheus;

namespace NekoHentai.API.Services
{
    public static class MangaMetrics
    {
        public static readonly Counter CacheHitsTotal = Metrics.CreateCounter(
            "nekohentai_cache_hits_total",
            "Total number of cache hits in Redis",
            new CounterConfiguration
            {
                LabelNames = new[] { "key_prefix" }
            });

        public static readonly Counter CacheMissesTotal = Metrics.CreateCounter(
            "nekohentai_cache_misses_total",
            "Total number of cache misses in Redis",
            new CounterConfiguration
            {
                LabelNames = new[] { "key_prefix" }
            });

        public static readonly Counter ChapterViewsIncrementedTotal = Metrics.CreateCounter(
            "nekohentai_chapter_views_incremented_total",
            "Total chapter view count increments recorded in Redis",
            new CounterConfiguration
            {
                LabelNames = new[] { "type" }
            });

        public static readonly Counter ChapterViewsSyncedTotal = Metrics.CreateCounter(
            "nekohentai_chapter_views_synced_total",
            "Total views synced from Redis to SQL Server in background worker");

        public static readonly Histogram DbSyncDurationSeconds = Metrics.CreateHistogram(
            "nekohentai_db_views_sync_duration_seconds",
            "Histogram of duration taken by ViewSyncWorker to batch update SQL Server views",
            new HistogramConfiguration
            {
                Buckets = Histogram.ExponentialBuckets(start: 0.005, factor: 2, count: 10)
            });

        public static readonly Gauge RedisConnectedGauge = Metrics.CreateGauge(
            "nekohentai_redis_connected",
            "Status of Redis connection (1 = connected, 0 = disconnected)");
    }
}
