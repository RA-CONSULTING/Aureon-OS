// Assets/Scripts/Nexus/Models.cs
using System;
using UnityEngine;

namespace Nexus
{
    [Serializable]
    public struct TensorDatum
    {
        public float phi;   // phase (rad)
        public float psi;   // amplitude density
        public float TSV;   // coherence 0..1-ish (toolkit-specific)
    }

    [Serializable]
    public struct SchumannFrame
    {
        public long timestampNanos;     // precise nanosecond timestamp
        public string label;            // optional human-readable label
        public float[] schumannHz;      // frequencies in Hz
        public TensorDatum[] tensorField;
        
        // Utility properties for live timestamp handling
        public double TimeSeconds => timestampNanos / 1_000_000_000.0;
        public string FormattedTime => NanoPrecisionTimer.FormatNanoseconds(timestampNanos);
    }

    [Serializable]
    public struct TriStream
    {
        public SchumannFrame[] past;
        public SchumannFrame[] present;
        public SchumannFrame[] future;
    }

    [Serializable]
    public struct WavePacket
    {
        public float[] frequencies;   // intent-derived Hz
        public float decay;           // seconds or unitless
        public string latticeId;      // who
        public bool observerLock;     // lock state
    }
}