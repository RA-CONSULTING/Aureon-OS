// Assets/Scripts/Nexus/SchumannFrameClip.cs
using System;
using UnityEngine;
using UnityEngine.Playables;
using UnityEngine.Timeline;

namespace NexusTimeline
{
    [Serializable]
    public class SchumannFrameClip : PlayableAsset, ITimelineClipAsset
    {
        public TextAsset frameData;
        public PlayMode playMode = PlayMode.Sequence;
        public float fps = 30f;
        public bool observerLock = false;
        public string latticeId = "Gary-02111991";
        public float amplitudeGain = 1.0f;

        public enum PlayMode { Sequence, Loop, Scrub }

        public ClipCaps clipCaps => ClipCaps.Blending;

        public override Playable CreatePlayable(PlayableGraph graph, GameObject owner)
        {
            var playable = ScriptPlayable<SchumannFrameBehaviour>.Create(graph);
            var behaviour = playable.GetBehaviour();
            
            behaviour.frameData = frameData;
            behaviour.playMode = playMode;
            behaviour.fps = fps;
            behaviour.observerLock = observerLock;
            behaviour.latticeId = latticeId;
            behaviour.amplitudeGain = amplitudeGain;
            
            return playable;
        }
    }
}