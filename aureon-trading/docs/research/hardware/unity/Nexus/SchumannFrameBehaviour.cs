// Assets/Scripts/Nexus/SchumannFrameBehaviour.cs
using System;
using System.Linq;
using UnityEngine;
using UnityEngine.Playables;
using Nexus;
namespace NexusTimeline
{
    [Serializable]
    public class SchumannFrameBehaviour : PlayableBehaviour
    {
        public TextAsset frameData;
        public SchumannFrameClip.PlayMode playMode;
        public float fps = 30f;
        public bool observerLock;
        public string latticeId;
        public float amplitudeGain = 1.0f;

        private SchumannFrame[] _frames;
        private float _anchorPhase;

        public override void OnPlayableCreate(Playable playable)
        {
            _frames = Parse(frameData);
            _anchorPhase = Nexus.LatticeIDSeal.AnchorPhase(latticeId);
        }

        public override void ProcessFrame(Playable playable, FrameData info, object playerData)
        {
            var boundRenderer = playerData as NexusLatticeRenderer;
            if (!boundRenderer || _frames == null || _frames.Length == 0) return;

            // Get current precise timestamp in nanoseconds
            long currentNanos = NanoPrecisionTimer.GetNanoseconds();
            
            SchumannFrame frame;
            double time = playable.GetTime();
            
            switch (playMode)
            {
                case SchumannFrameClip.PlayMode.Sequence:
                    frame = GetFrameByTimeSequence(currentNanos);
                    break;
                case SchumannFrameClip.PlayMode.Loop:
                    frame = GetFrameByTimeLoop(currentNanos);
                    break;
                case SchumannFrameClip.PlayMode.Scrub:
                    float t = Mathf.Clamp01((float)(time / playable.GetDuration()));
                    int scrubIndex = Mathf.FloorToInt(t * (_frames.Length - 1));
                    frame = _frames[scrubIndex];
                    break;
                default:
                    frame = _frames[0];
                    break;
            }

            if (observerLock)
            {
                frame = PickPrime(_frames, _anchorPhase);
            }

            // Update frame timestamp to current precise time
            frame.timestampNanos = currentNanos;

            var packet = new WavePacket
            {
                frequencies = frame.schumannHz ?? Array.Empty<float>(),
                decay = 8f,
                latticeId = latticeId,
                observerLock = observerLock
            };

            boundRenderer.ApplyWave(packet, info.weight, amplitudeGain);
        }

        private SchumannFrame GetFrameByTimeSequence(long currentNanos)
        {
            if (_frames.Length == 0) return default;
            
            // Find frame with closest timestamp or use fps-based indexing
            long minDiff = long.MaxValue;
            int bestIndex = 0;
            
            for (int i = 0; i < _frames.Length; i++)
            {
                long diff = Math.Abs(_frames[i].timestampNanos - currentNanos);
                if (diff < minDiff)
                {
                    minDiff = diff;
                    bestIndex = i;
                }
            }
            
            return _frames[bestIndex];
        }

        private SchumannFrame GetFrameByTimeLoop(long currentNanos)
        {
            if (_frames.Length == 0) return default;
            
            // Use modulo for looping based on nanosecond precision
            long totalDuration = _frames[_frames.Length - 1].timestampNanos - _frames[0].timestampNanos;
            if (totalDuration <= 0) return _frames[0];
            
            long loopTime = currentNanos % totalDuration;
            return GetFrameByTimeSequence(_frames[0].timestampNanos + loopTime);
        }

        SchumannFrame[] Parse(TextAsset ta)
        {
            if (!ta) return Array.Empty<SchumannFrame>();
            var wrapped = JsonUtility.FromJson<FrameArray>("{\"items\":" + ta.text + "}");
            return wrapped?.items ?? Array.Empty<SchumannFrame>();
        }

        [Serializable] 
        class FrameArray { public SchumannFrame[] items; }

        static SchumannFrame PickPrime(SchumannFrame[] frames, float anchor)
        {
            int bi = 0; 
            float best = -1f;
            for (int i = 0; i < frames.Length; i++)
            {
                var tf = frames[i].tensorField;
                if (tf == null || tf.Length == 0) continue;
                float meanPhi = tf.Average(d => d.phi);
                float dphi = Mathf.Acos(Mathf.Cos(meanPhi - anchor));
                float meanPsi = tf.Average(d => Mathf.Abs(d.psi));
                float s = (1f - (dphi / Mathf.PI)) * (0.6f + 0.4f * Mathf.Clamp01(meanPsi));
                if (s > best) { best = s; bi = i; }
            }
            return frames[Mathf.Clamp(bi, 0, frames.Length - 1)];
        }
    }
}