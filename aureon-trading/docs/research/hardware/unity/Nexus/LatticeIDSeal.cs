// Assets/Scripts/Nexus/LatticeIDSeal.cs
using System;

namespace Nexus
{
    public static class LatticeIDSeal
    {
        /// <summary>
        /// Deterministic phase anchor in [0, 2π) from an ID.
        /// </summary>
        public static float AnchorPhase(string latticeId)
        {
            if (string.IsNullOrEmpty(latticeId)) return 0f;
            unchecked
            {
                uint h = 0;
                for (int i = 0; i < latticeId.Length; i++)
                    h = (h * 131u) + latticeId[i];
                return (h % 10000u) / 10000f * (float)(Math.PI * 2.0);
            }
        }

        /// <summary>
        /// Soft safety clamp for amplitude.
        /// </summary>
        public static float SafeGain(float requested, float cap = 3f) =>
            Math.Clamp(requested, 0.2f, cap);
    }
}