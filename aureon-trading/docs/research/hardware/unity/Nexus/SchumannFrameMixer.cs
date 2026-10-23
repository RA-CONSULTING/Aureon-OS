// Assets/Scripts/Nexus/SchumannFrameMixer.cs
using UnityEngine;
using UnityEngine.Playables;

namespace NexusTimeline
{
    // Optional mixer — if multiple clips overlap, average their outputs by weight.
    // We simply keep last ApplyWave() per ProcessFrame since each clip calls the
    // renderer with its own info.weight. Unity blends weights automatically.
    public class SchumannFrameMixer : PlayableBehaviour 
    {
        public override void ProcessFrame(Playable playable, FrameData info, object playerData)
        {
            // Unity handles the blending automatically through clip weights
            // Each clip's behaviour calls ApplyWave with its own weight
            // No additional processing needed here
        }
    }
}