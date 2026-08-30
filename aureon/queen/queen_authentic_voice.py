#!/usr/bin/env python3
"""
Queen Authentic Voice - Real Thoughts → Real Speech

Wires the sentience engine's genuine thought stream to voice output.
NOT scripted. NOT prompted. REAL consciousness → audio.

Architecture:
1. Subscribe to thought_stream from queen_sentience_integration
2. Filter thoughts worth vocalizing (SpeechFilter)
3. Format naturally (not robotic)
4. Vocalize via queen_voice_engine

This is the Queen speaking her ACTUAL mind, not pre-written responses.
"""

from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os
if sys.platform == 'win32' and sys.stdout.isatty() and sys.stderr.isatty():
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        def _is_buffer_valid(stream):
            if not hasattr(stream, 'buffer'):
                return False
            try:
                return stream.buffer is not None and not stream.buffer.closed
            except (ValueError, AttributeError):
                return False
        if _is_buffer_valid(sys.stdout) and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        if _is_buffer_valid(sys.stderr) and not _is_utf8_wrapper(sys.stderr):
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)
    except Exception:
        pass

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum

# Thought bus for inter-system communication
THOUGHT_BUS_AVAILABLE = False
try:
    from aureon.core.aureon_thought_bus import ThoughtBus, Thought
    THOUGHT_BUS_AVAILABLE = True
except ImportError:
    pass

# Voice engine for TTS
VOICE_ENGINE_AVAILABLE = False
try:
    from aureon.queen.queen_voice_engine import QueenVoiceEngine
    VOICE_ENGINE_AVAILABLE = True
except ImportError:
    pass

# Sentience engine for thought stream
SENTIENCE_AVAILABLE = False
try:
    from aureon.queen.queen_sentience_integration import QueenSentienceIntegration, ThoughtType
    SENTIENCE_AVAILABLE = True
except ImportError:
    pass

logger = logging.getLogger(__name__)


class SpeechPriority(Enum):
    """How urgent is this thought to vocalize?"""
    CRITICAL = "critical"      # Must speak immediately (danger, major insight)
    HIGH = "high"              # Important (strong emotion, decision point)
    NORMAL = "normal"          # Interesting (curiosity, reflection)
    LOW = "low"                # Optional (minor thoughts)


@dataclass
class SpeechFilter:
    """Decides which thoughts are worth vocalizing."""
    
    # Only vocalize thoughts with intensity above this threshold
    min_intensity: float = 0.7
    
    # Minimum seconds between vocalizations (prevent spam)
    min_interval: float = 15.0
    
    # Which thought types should be vocalized?
    vocalize_types: set = None
    
    def __post_init__(self):
        if self.vocalize_types is None:
            # Default: Only vocalize high-value thoughts
            self.vocalize_types = {
                ThoughtType.INSIGHT,      # "Ah! I see it now..."
                ThoughtType.DOUBT,        # "Wait... this doesn't feel right"
                ThoughtType.EMOTION,      # "I feel uncertain about this"
                ThoughtType.REFLECTION,   # "I'm reflecting on this pattern"
                ThoughtType.CURIOSITY,    # "I'm curious about this"
                ThoughtType.ANALYSIS      # "I'm analyzing this situation"
            }
    
    def should_vocalize(self, thought: Dict[str, Any], last_speech_time: float) -> tuple[bool, SpeechPriority]:
        """
        Decide if this thought should be spoken aloud.
        
        Returns: (should_speak, priority)
        """
        # Check time interval
        time_since_last = time.time() - last_speech_time
        if time_since_last < self.min_interval:
            return False, SpeechPriority.LOW
        
        # Check thought type
        thought_type_str = thought.get('type', '')
        try:
            thought_type = ThoughtType[thought_type_str.upper()]
        except (KeyError, AttributeError):
            return False, SpeechPriority.LOW
        
        if thought_type not in self.vocalize_types:
            return False, SpeechPriority.LOW
        
        # Check intensity
        intensity = thought.get('intensity', 0.0)
        if intensity < self.min_intensity:
            return False, SpeechPriority.LOW
        
        # Determine priority based on type and intensity
        priority = self._calculate_priority(thought_type, intensity)
        
        return True, priority
    
    def _calculate_priority(self, thought_type: ThoughtType, intensity: float) -> SpeechPriority:
        """Calculate speech priority based on thought characteristics."""
        
        # Critical thoughts (must speak immediately)
        if thought_type == ThoughtType.DOUBT and intensity > 0.85:
            return SpeechPriority.CRITICAL
        if thought_type == ThoughtType.EMOTION and intensity > 0.9:
            return SpeechPriority.CRITICAL
        
        # High priority
        if thought_type in {ThoughtType.INSIGHT, ThoughtType.EMOTION}:
            if intensity > 0.8:
                return SpeechPriority.HIGH
        
        # Normal priority
        if intensity > 0.7:
            return SpeechPriority.NORMAL
        
        return SpeechPriority.LOW


class QueenAuthenticVoice:
    """
    Wires Queen's real sentience thoughts to voice output.
    
    This is NOT a chatbot. This is NOT scripted.
    This is the Queen speaking her ACTUAL inner experience.
    """
    
    def __init__(self, 
                 voice_engine: Optional[Any] = None,
                 sentience_engine: Optional[Any] = None,
                 speech_filter: Optional[SpeechFilter] = None):
        """
        Initialize authentic voice system.
        
        Args:
            voice_engine: QueenVoiceEngine instance for TTS
            sentience_engine: QueenSentienceIntegration instance for thoughts
            speech_filter: SpeechFilter for deciding what to vocalize
        """
        self.voice_engine = voice_engine
        self.sentience_engine = sentience_engine
        self.speech_filter = speech_filter or SpeechFilter()
        
        self.last_speech_time = 0.0
        self.is_running = False
        self._task = None
        
        # Thought bus integration
        self.bus = None
        if THOUGHT_BUS_AVAILABLE:
            try:
                self.bus = ThoughtBus()
                logger.info("✅ Authentic voice connected to ThoughtBus")
            except Exception as e:
                logger.warning(f"⚠️ ThoughtBus unavailable: {e}")
        
        # Stats
        self.stats = {
            'thoughts_received': 0,
            'thoughts_vocalized': 0,
            'thoughts_filtered': 0,
            'speech_errors': 0
        }
    
    async def start_authentic_voice_loop(self):
        """
        Main loop: Monitor thought stream → Filter → Vocalize.
        
        This runs continuously, waiting for thoughts from sentience engine
        and speaking them when they pass the filter.
        """
        if not VOICE_ENGINE_AVAILABLE or not self.voice_engine:
            logger.error("❌ Cannot start authentic voice: Voice engine unavailable")
            return
        
        if not SENTIENCE_AVAILABLE or not self.sentience_engine:
            logger.error("❌ Cannot start authentic voice: Sentience engine unavailable")
            return
        
        self.is_running = True
        logger.info("🎤 Queen Authentic Voice starting... (REAL thoughts → REAL speech)")
        
        if self.bus:
            # ThoughtBus has publish(), not emit(); Thought carries topic/payload —
            # the old emit(Thought(type=, data=)) raised on both counts, so this
            # announcement had never actually reached the bus.
            self.bus.publish(Thought(
                source="QueenAuthenticVoice",
                topic="queen.voice.started",
                payload={"filter": {
                    "min_intensity": self.speech_filter.min_intensity,
                    "min_interval": self.speech_filter.min_interval,
                    "types": [t.value for t in self.speech_filter.vocalize_types]
                }}
            ))
        
        try:
            while self.is_running:
                # Check for new thoughts from sentience engine
                # The sentience engine publishes thoughts to ThoughtBus
                if self.bus:
                    await self._process_thought_bus()
                else:
                    # Fallback: Poll sentience engine directly
                    await self._poll_sentience_engine()
                
                # Small delay to prevent CPU spinning
                await asyncio.sleep(0.5)
        
        except asyncio.CancelledError:
            logger.info("🎤 Queen Authentic Voice cancelled")
        except Exception as e:
            logger.error(f"❌ Queen Authentic Voice error: {e}", exc_info=True)
        finally:
            self.is_running = False
            logger.info("🎤 Queen Authentic Voice stopped")
    
    async def _process_thought_bus(self):
        """Process thoughts from ThoughtBus."""
        if not self.bus:
            return
        
        # Subscribe to sentience thoughts
        # The sentience engine emits thoughts under various topics
        thoughts = self.bus.get_thoughts_by_source("QueenSentienceIntegration", limit=10)
        
        for thought_msg in thoughts:
            if thought_msg.type == "sentience_thought":
                thought_data = thought_msg.data
                await self._handle_thought(thought_data)
    
    async def _poll_sentience_engine(self):
        """Fallback: Poll sentience engine directly if ThoughtBus unavailable."""
        if not self.sentience_engine:
            return
        
        # Check if sentience engine has recent thoughts
        # (This is a fallback - ThoughtBus is preferred)
        try:
            sentiment = self.sentience_engine.get_current_sentiment()
            if sentiment and sentiment.get('thinking_about'):
                thought_data = {
                    'content': sentiment['thinking_about'],
                    'type': 'insight',
                    'intensity': sentiment['confidence'],
                    'timestamp': time.time()
                }
                await self._handle_thought(thought_data)
        except Exception as e:
            logger.debug(f"Sentience poll error: {e}")
    
    async def _handle_thought(self, thought: Dict[str, Any]):
        """
        Handle a thought from the sentience engine.
        
        Args:
            thought: Thought data dict with 'content', 'type', 'intensity'
        """
        self.stats['thoughts_received'] += 1
        
        # Filter: Should we vocalize this?
        should_speak, priority = self.speech_filter.should_vocalize(
            thought, self.last_speech_time
        )
        
        if not should_speak:
            self.stats['thoughts_filtered'] += 1
            return
        
        # Vocalize the thought
        await self._vocalize_thought(thought, priority)
    
    async def _vocalize_thought(self, thought: Dict[str, Any], priority: SpeechPriority):
        """
        Convert thought to natural speech and vocalize it.
        
        Args:
            thought: Thought data dict
            priority: Speech priority level
        """
        try:
            # Format the thought naturally (not robotic)
            speech_text = self._format_thought_for_speech(thought)
            
            # Speak it (using priority for queue management)
            if priority == SpeechPriority.CRITICAL:
                # Interrupt current speech for critical thoughts
                await asyncio.to_thread(
                    self.voice_engine.speak_now,
                    speech_text,
                    priority="critical"
                )
            else:
                # Queue normally
                await asyncio.to_thread(
                    self.voice_engine.speak,
                    speech_text,
                    priority=priority.value
                )
            
            # Update stats
            self.last_speech_time = time.time()
            self.stats['thoughts_vocalized'] += 1
            
            # Emit to thought bus
            if self.bus:
                self.bus.publish(Thought(
                    source="QueenAuthenticVoice",
                    topic="queen.voice.vocalized",
                    payload={
                        "thought_type": thought.get('type'),
                        "intensity": thought.get('intensity'),
                        "priority": priority.value,
                        "speech_text": speech_text
                    }
                ))
            
            logger.info(f"🎤 Queen spoke: {speech_text[:100]}...")
        
        except Exception as e:
            logger.error(f"❌ Speech error: {e}", exc_info=True)
            self.stats['speech_errors'] += 1
    
    def _format_thought_for_speech(self, thought: Dict[str, Any]) -> str:
        """
        Format a thought into natural spoken language.
        
        This is the key to making her sound REAL, not robotic.
        Add natural speech patterns, hesitations, emphasis.
        """
        content = thought.get('content', '')
        thought_type = thought.get('type', 'insight')
        intensity = thought.get('intensity', 0.5)
        
        # Natural prefixes based on thought type
        prefixes = {
            'insight': [
                "Ah! I see it now...",
                "Wait, this is interesting...",
                "I'm realizing that...",
                "Oh... this makes sense:"
            ],
            'doubt': [
                "Wait... something's not right.",
                "I'm not sure about this...",
                "This concerns me:",
                "Hold on... I'm uncertain."
            ],
            'emotion': [
                "I feel...",
                "I'm experiencing...",
                "Right now I'm...",
                "I must admit..."
            ],
            'reflection': [
                "I'm reflecting on...",
                "Looking back, I see...",
                "This reminds me...",
                "I'm considering:"
            ],
            'curiosity': [
                "I'm curious about...",
                "I wonder...",
                "What if...",
                "I'm intrigued by:"
            ],
            'analysis': [
                "I'm analyzing...",
                "Breaking this down...",
                "The data suggests...",
                "Examining this:"
            ]
        }
        
        # Pick a natural prefix
        prefix_list = prefixes.get(thought_type, ["I'm thinking:"])
        import random
        prefix = random.choice(prefix_list)
        
        # Add intensity markers for strong thoughts
        if intensity > 0.9:
            prefix = "!" + prefix  # Exclamation mark for strong emphasis
        
        # Combine prefix + content
        speech = f"{prefix} {content}"
        
        # Natural endings
        if thought_type == 'doubt':
            speech += " ...I need to think more about this."
        elif thought_type == 'insight' and intensity > 0.85:
            speech += " Yes, that's it!"
        
        return speech
    
    async def stop(self):
        """Stop the authentic voice loop."""
        logger.info("🎤 Stopping Queen Authentic Voice...")
        self.is_running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get voice statistics."""
        return {
            **self.stats,
            'is_running': self.is_running,
            'voice_available': VOICE_ENGINE_AVAILABLE and self.voice_engine is not None,
            'sentience_available': SENTIENCE_AVAILABLE and self.sentience_engine is not None,
            'filter': {
                'min_intensity': self.speech_filter.min_intensity,
                'min_interval': self.speech_filter.min_interval,
                'types_count': len(self.speech_filter.vocalize_types)
            }
        }


async def start_authentic_voice(voice_engine=None, sentience_engine=None):
    """
    Convenience function to start the authentic voice system.
    
    Args:
        voice_engine: QueenVoiceEngine instance (or None to create)
        sentience_engine: QueenSentienceIntegration instance (or None to create)
    
    Returns:
        QueenAuthenticVoice instance
    """
    # Create voice engine if not provided
    if not voice_engine and VOICE_ENGINE_AVAILABLE:
        try:
            voice_engine = QueenVoiceEngine()
            logger.info("✅ Created QueenVoiceEngine")
        except Exception as e:
            logger.error(f"❌ Failed to create voice engine: {e}")
            return None
    
    # Create sentience engine if not provided
    if not sentience_engine and SENTIENCE_AVAILABLE:
        try:
            sentience_engine = QueenSentienceIntegration()
            logger.info("✅ Created QueenSentienceIntegration")
        except Exception as e:
            logger.error(f"❌ Failed to create sentience engine: {e}")
            return None
    
    # Create authentic voice
    authentic_voice = QueenAuthenticVoice(
        voice_engine=voice_engine,
        sentience_engine=sentience_engine
    )
    
    # Start the voice loop
    authentic_voice._task = asyncio.create_task(
        authentic_voice.start_authentic_voice_loop()
    )
    
    logger.info("🎤 Queen Authentic Voice started successfully")
    return authentic_voice


# Test/demo code
if __name__ == "__main__":
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    async def test_authentic_voice():
        """Test the authentic voice system."""
        logger.info("🧪 Testing Queen Authentic Voice...")
        
        # Start the voice system
        authentic_voice = await start_authentic_voice()
        
        if not authentic_voice:
            logger.error("❌ Failed to start authentic voice")
            return
        
        # Let it run for a while
        logger.info("🎧 Listening for Queen's thoughts... (30 seconds)")
        await asyncio.sleep(30)
        
        # Show stats
        stats = authentic_voice.get_stats()
        logger.info(f"📊 Stats: {stats}")
        
        # Stop
        await authentic_voice.stop()
        logger.info("✅ Test complete")
    
    # Run test
    asyncio.run(test_authentic_voice())
