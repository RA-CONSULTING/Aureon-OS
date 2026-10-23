// Assets/Scripts/Nexus/TriTimelineBlender.cs
using System;
using System.Linq;
using UnityEngine;

namespace Nexus
{
    public static class TriTimelineBlender
    {
        public struct Weights { public float past, present, future; }

        static float Clamp01(float x) => Mathf.Clamp01(x);

        public static SchumannFrame? PickPrime(SchumannFrame[] frames, float anchorPhase)
        {
            if (frames == null || frames.Length == 0) return null;

            float Score(in SchumannFrame fr)
            {
                var tf = fr.tensorField;
                if (tf == null || tf.Length == 0) return 0f;

                float meanPhi = tf.Average(d => d.phi);
                float dphi = Mathf.Acos(Mathf.Cos(meanPhi - anchorPhase));
                float meanPsi = tf.Average(d => Mathf.Abs(d.psi));
                float phaseScore = 1f - (dphi / Mathf.PI);
                float cohScore = 0.6f + 0.4f * Clamp01(meanPsi);
                return phaseScore * cohScore;
            }

            int bestI = 0;
            float bestS = -1f;
            for (int i = 0; i < frames.Length; i++)
            {
                float s = Score(frames[i]);
                if (s > bestS) { bestS = s; bestI = i; }
            }
            return frames[bestI];
        }

        public static SchumannFrame Blend(SchumannFrame? a, SchumannFrame? b, SchumannFrame? c, Weights w)
        {
            float sw = w.past + w.present + w.future; if (sw <= 1e-6f) sw = 1f;
            float wa = w.past / sw, wb = w.present / sw, wc = w.future / sw;

            int longest = new[] { a?.schumannHz?.Length ?? 0, b?.schumannHz?.Length ?? 0, c?.schumannHz?.Length ?? 0 }.Max();
            if (longest <= 0) longest = 1;

            float[] hz = new float[longest];
            for (int i = 0; i < longest; i++)
            {
                float av = a?.schumannHz != null ? (i < a.Value.schumannHz.Length ? a.Value.schumannHz[i] : a.Value.schumannHz[^1]) : 0f;
                float bv = b?.schumannHz != null ? (i < b.Value.schumannHz.Length ? b.Value.schumannHz[i] : b.Value.schumannHz[^1]) : 0f;
                float cv = c?.schumannHz != null ? (i < c.Value.schumannHz.Length ? c.Value.schumannHz[i] : c.Value.schumannHz[^1]) : 0f;
                hz[i] = av * wa + bv * wb + cv * wc;
            }

            var list = new System.Collections.Generic.List<TensorDatum>();
            if (a?.tensorField != null) foreach (var d in a.Value.tensorField) list.Add(new TensorDatum { phi = d.phi, psi = d.psi * wa, TSV = d.TSV });
            if (b?.tensorField != null) foreach (var d in b.Value.tensorField) list.Add(new TensorDatum { phi = d.phi, psi = d.psi * wb, TSV = d.TSV });
            if (c?.tensorField != null) foreach (var d in c.Value.tensorField) list.Add(new TensorDatum { phi = d.phi, psi = d.psi * wc, TSV = d.TSV });

            return new SchumannFrame
            {
                timestampNanos = NanoPrecisionTimer.GetNanoseconds(),
                label = $"{a?.label ?? ""} ⊕ {b?.label ?? ""} ⊕ {c?.label ?? ""}",
                schumannHz = hz,
                tensorField = list.ToArray()
            };
        }
    }
}