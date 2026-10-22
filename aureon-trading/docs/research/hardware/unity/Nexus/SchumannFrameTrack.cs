// Assets/Scripts/Nexus/SchumannFrameTrack.cs
using UnityEngine;
using UnityEngine.Playables;
using UnityEngine.Timeline;

namespace NexusTimeline
{
    [TrackColor(0.30f, 0.65f, 0.95f)]
    [TrackBindingType(typeof(NexusLatticeRenderer))]
    [TrackClipType(typeof(SchumannFrameClip))]
    public class SchumannFrameTrack : TrackAsset
    {
        public override Playable CreateTrackMixer(PlayableGraph graph, GameObject go, int inputCount)
        {
            return ScriptPlayable<SchumannFrameMixer>.Create(graph, inputCount);
        }

        public override void GatherProperties(PlayableDirector director, IPropertyCollector driver)
        {
            // Gather any properties that need to be animated
            var binding = director.GetGenericBinding(this) as NexusLatticeRenderer;
            if (binding != null)
            {
                // Register properties for animation if needed
            }
        }
    }
}