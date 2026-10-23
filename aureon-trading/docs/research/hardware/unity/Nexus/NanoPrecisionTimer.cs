// Assets/Scripts/Nexus/NanoPrecisionTimer.cs
using System;
using System.Diagnostics;

namespace Nexus
{
    public static class NanoPrecisionTimer
    {
        private static readonly long _startTicks = Stopwatch.GetTimestamp();
        private static readonly double _ticksToNanos = 1_000_000_000.0 / Stopwatch.Frequency;
        
        /// <summary>
        /// Get current high-precision timestamp in nanoseconds since Unix epoch (live time)
        /// </summary>
        public static long GetNanoseconds()
        {
            return GetUtcNanoseconds();
        }
        
        /// <summary>
        /// Get UTC timestamp in nanoseconds since Unix epoch
        /// </summary>
        public static long GetUtcNanoseconds()
        {
            var utcNow = DateTime.UtcNow;
            var unixEpoch = new DateTime(1970, 1, 1, 0, 0, 0, DateTimeKind.Utc);
            var elapsed = utcNow - unixEpoch;
            
            // Add high-precision component from Stopwatch
            long baseTicks = elapsed.Ticks;
            long precisionTicks = (Stopwatch.GetTimestamp() - _startTicks) % TimeSpan.TicksPerMillisecond;
            
            return (baseTicks + precisionTicks) * 100; // Convert to nanoseconds
        }
        
        /// <summary>
        /// Convert nanoseconds to human-readable timestamp string
        /// </summary>
        public static string FormatNanoseconds(long nanos)
        {
            // Convert nanoseconds since Unix epoch to DateTime
            double seconds = nanos / 1_000_000_000.0;
            var dateTime = DateTimeOffset.FromUnixTimeSeconds((long)seconds).ToLocalTime();
            long nanoRemainder = nanos % 1_000_000_000;
            
            return $"{dateTime:MM/dd/yyyy, HH:mm:ss}.{nanoRemainder:D9}";
        }
    }
}