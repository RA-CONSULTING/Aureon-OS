from __future__ import annotations

import base64
import json
import os
import sys
import threading
import time
import uuid
from dataclasses import dataclass, asdict, field
from typing import Any, Callable, Deque, Dict, List, Optional
from collections import deque

# Cross-platform file locking
if sys.platform == 'win32':
    import msvcrt
    def _lock_file(f):
        msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
    def _unlock_file(f):
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except Exception:
            pass
else:
    import fcntl
    def _lock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
    def _unlock_file(f):
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)

Json = Dict[str, Any]


def _now() -> float:
    return time.time()


def _coerce_thought_args(*args: Any, **kwargs: Any) -> "Thought":
    if len(args) == 1 and isinstance(args[0], Thought):
        return args[0]

    if len(args) == 1 and all(hasattr(args[0], attr) for attr in ("source", "topic", "payload")):
        foreign = args[0]
        payload = getattr(foreign, "payload", {}) or {}
        meta = getattr(foreign, "meta", {}) or {}
        payload_encoding = getattr(foreign, "payload_encoding", "json") or "json"
        binary_payload_b64 = getattr(foreign, "binary_payload_b64", None)
        return Thought(
            id=str(getattr(foreign, "id", "") or str(uuid.uuid4())),
            ts=float(getattr(foreign, "ts", _now()) or _now()),
            source=str(getattr(foreign, "source", "unknown") or "unknown"),
            topic=str(getattr(foreign, "topic", "thought") or "thought"),
            trace_id=str(getattr(foreign, "trace_id", "") or str(uuid.uuid4())),
            parent_id=getattr(foreign, "parent_id", None),
            payload=dict(payload) if isinstance(payload, dict) else {"value": payload},
            meta=dict(meta) if isinstance(meta, dict) else {"value": meta},
            payload_encoding=str(payload_encoding),
            binary_payload_b64=binary_payload_b64,
        )

    if len(args) == 1 and isinstance(args[0], dict):
        payload = dict(args[0])
        topic = str(payload.pop("topic", kwargs.pop("topic", "thought")))
        source = str(payload.pop("source", kwargs.pop("source", "unknown")))
        meta = kwargs.pop("meta", None) or payload.pop("meta", None) or {}
        return Thought(source=source, topic=topic, payload=payload, meta=dict(meta))

    if args and isinstance(args[0], str):
        topic = args[0]
        payload = {}
        if len(args) >= 2 and isinstance(args[1], dict):
            payload = dict(args[1])
        source = str(kwargs.pop("source", payload.pop("source", "unknown")))
        meta = kwargs.pop("meta", None) or payload.pop("meta", None) or {}
        trace_id = kwargs.pop("trace_id", None) or payload.pop("trace_id", None)
        parent_id = kwargs.pop("parent_id", None) or payload.pop("parent_id", None)
        return Thought(
            source=source,
            topic=topic,
            payload=payload,
            meta=dict(meta),
            trace_id=trace_id or str(uuid.uuid4()),
            parent_id=parent_id,
        )

    raise TypeError("publish() expects a Thought, dict, or topic/payload arguments")


@dataclass
class Thought:
    """
    A unified JSON envelope for *every* internal message.
    This is how different parts of the system "think" and communicate.
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ts: float = field(default_factory=_now)

    source: str = "unknown"
    topic: str = "thought"  # e.g. market.snapshot, miner.signal, risk.approval, execution.order

    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: Optional[str] = None

    payload: Json = field(default_factory=dict)
    meta: Json = field(default_factory=dict)
    payload_encoding: str = "json"
    binary_payload_b64: Optional[str] = None

    def to_json(self) -> Json:
        return asdict(self)


# ═══════════════════════════════════════════════════════════════════════════════
# FILE-BASED THOUGHT BUS (LOCAL DEVELOPMENT)
# ═══════════════════════════════════════════════════════════════════════════════

class FileThoughtBus:
    """
    File-based ThoughtBus for local development.
    Uses JSONL files for persistence and in-memory pub/sub.
    """
    
    def __init__(self, state_file: str = "aureon_thought_bus.jsonl"):
        self.state_file = state_file
        self.subscriptions: Dict[str, List[Callable]] = {}
        self._lock = threading.Lock()
        
        # Load existing thoughts
        self._load_history()
    
    def _load_history(self):
        """Load thought history from file."""
        if not os.path.exists(self.state_file):
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        thought_data = json.loads(line.strip())
                        # Could store in memory if needed for history
        except Exception as e:
            print(f"Warning: Could not load thought history: {e}")
    
    def _save_thought(self, thought: Thought):
        """Save thought to file."""
        try:
            with self._lock:
                with open(self.state_file, 'a', encoding='utf-8') as f:
                    json.dump(asdict(thought), f)
                    f.write('\n')
        except Exception as e:
            print(f"Warning: Could not save thought: {e}")
    
    def publish(self, *args: Any, **kwargs: Any):
        """Publish a thought to all matching subscribers."""
        thought = _coerce_thought_args(*args, **kwargs)
        self._save_thought(thought)
        
        # Find matching handlers
        for sub_topic, handlers in self.subscriptions.items():
            if self._topic_matches(thought.topic, sub_topic):
                for handler in handlers:
                    try:
                        handler(thought)
                    except Exception as e:
                        print(f"Error in handler for topic {thought.topic}: {e}")
    
    def subscribe(self, topic: str, handler: Callable):
        """Subscribe a handler to a topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
        self.subscriptions[topic].append(handler)
    
    def _topic_matches(self, topic: str, subscription: str) -> bool:
        """Check if a topic matches a subscription pattern."""
        if subscription == "*":
            return True
        if subscription.endswith(".*"):
            return topic.startswith(subscription[:-1])
        return topic == subscription


# ═══════════════════════════════════════════════════════════════════════════════
# REDIS-BACKED THOUGHT BUS (PRODUCTION)
# ═══════════════════════════════════════════════════════════════════════════════

class RedisThoughtBus:
    """
    Redis-backed ThoughtBus for production deployment.
    Provides 100% connectivity and data streaming.
    """
    
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.stream_name = "aureon_thought_stream"
        self.pubsub_channel_prefix = "aureon_pubsub:"
        
        try:
            import redis
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            print("🧠 RedisThoughtBus: CONNECTED to Redis")
        except ImportError:
            raise ImportError("redis package not installed. Install with: pip install redis")
        except Exception as e:
            raise ConnectionError(f"Could not connect to Redis: {e}")
        
        self.subscriptions: Dict[str, List[Callable]] = {}
        self.pubsub = self.redis_client.pubsub(ignore_subscribe_messages=True)
        self.listener_thread = None
        self._running = False
    
    def _listener_loop(self):
        """Listen for messages on subscribed channels."""
        print("📡 Redis listener thread started")
        for message in self.pubsub.listen():
            if not self._running:
                break
            
            try:
                channel = message['channel']
                topic = channel.replace(self.pubsub_channel_prefix, "")
                thought_data = json.loads(message['data'])
                thought = Thought(**thought_data)
                
                # Find matching handlers
                for sub_topic, handlers in self.subscriptions.items():
                    if self._topic_matches(topic, sub_topic):
                        for handler in handlers:
                            try:
                                handler(thought)
                            except Exception as e:
                                print(f"Error in handler for topic {topic}: {e}")
            except Exception as e:
                print(f"Error processing Redis message: {e}")
        
        print("📡 Redis listener thread stopped")
    
    def _topic_matches(self, topic: str, subscription: str) -> bool:
        """Check if a topic matches a subscription pattern."""
        if subscription == "*":
            return True
        if subscription.endswith(".*"):
            return topic.startswith(subscription[:-1])
        return topic == subscription
    
    def publish(self, *args: Any, **kwargs: Any):
        """Publish a thought to Redis."""
        thought = _coerce_thought_args(*args, **kwargs)
        try:
            thought_json = json.dumps(asdict(thought))
            
            # Publish to Pub/Sub channel
            channel = f"{self.pubsub_channel_prefix}{thought.topic}"
            self.redis_client.publish(channel, thought_json)
            
            # Add to Stream for persistence
            self.redis_client.xadd(self.stream_name, {'thought': thought_json})
            
        except Exception as e:
            print(f"Failed to publish thought to Redis: {e}")
    
    def subscribe(self, topic: str, handler: Callable):
        """Subscribe a handler to a topic."""
        if topic not in self.subscriptions:
            self.subscriptions[topic] = []
            
            # Subscribe to the channel pattern
            channel_pattern = f"{self.pubsub_channel_prefix}{topic}"
            self.pubsub.psubscribe(channel_pattern)
            
        self.subscriptions[topic].append(handler)
    
    def start(self):
        """Start the background listener thread."""
        if not self._running:
            self._running = True
            self.listener_thread = threading.Thread(target=self._listener_loop, daemon=True)
            self.listener_thread.start()
    
    def stop(self):
        """Stop the background listener thread."""
        if self._running:
            self._running = False
            self.pubsub.unsubscribe()
            if self.listener_thread:
                self.listener_thread.join(timeout=2)
            print("RedisThoughtBus stopped")


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS (AUTO-DETECTS ENVIRONMENT)
# ═══════════════════════════════════════════════════════════════════════════════

_thought_bus_instance: Optional[Any] = None
_bus_lock = threading.Lock()

def get_thought_bus() -> Any:
    """
    Get the singleton ThoughtBus instance.
    
    Automatically chooses the appropriate implementation:
    - RedisThoughtBus if AUREON_REDIS_URL is set (production)
    - FileThoughtBus for local development
    
    This ensures 100% connectivity in production while maintaining
    ease of development locally.
    """
    global _thought_bus_instance
    
    with _bus_lock:
        if _thought_bus_instance is None:
            redis_url = os.getenv("AUREON_REDIS_URL")
            
            if redis_url:
                print("🧠 Using RedisThoughtBus (production mode)")
                _thought_bus_instance = RedisThoughtBus(redis_url)
                _thought_bus_instance.start()
            else:
                print("🧠 Using FileThoughtBus (development mode)")
                _thought_bus_instance = FileThoughtBus()
    
    return _thought_bus_instance


# ═══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def think(payload: Any = None, topic: str = "thought", source: str = "unknown", **kwargs) -> Thought:
    """
    Convenience function to create and publish a thought.
    
    Usage:
        think({"symbol": "BTC/USD", "price": 60000}, topic="market.update")
    """
    thought = Thought(
        source=source,
        topic=topic,
        payload=payload or {},
        **kwargs
    )
    
    bus = get_thought_bus()
    bus.publish(thought)
    
    return thought


Subscriber = Callable[[Thought], None]


class ThoughtBus:
    def __init__(self, max_memory: int = 5000, persist_path: Optional[str] = None):
        self._lock = threading.RLock()
        self._subs: Dict[str, List[Subscriber]] = {}
        self._memory: Deque[Thought] = deque(maxlen=max_memory)
        self._persist_path = persist_path

        if self._persist_path:
            os.makedirs(os.path.dirname(self._persist_path) or ".", exist_ok=True)
            
        # Auto-wire Whale Sonar for normal runtime, but keep audit probes inert.
        if os.getenv("AUREON_AUDIT_MODE", "").strip().lower() not in {"1", "true", "yes", "on"}:
            try:
                from aureon.core.mycelium_whale_sonar import ensure_sonar
                try:
                    ensure_sonar(self)
                except Exception:
                    # E.g. circular import or missing dependency during startup; proceed anyway.
                    pass
            except ImportError:
                # Mycelium sonar module might not be present in all environments
                pass

    def think(self, message: str, topic: str = "thought", priority: str = "normal", metadata: Dict = None) -> Thought:
        """Convenience method to publish a thought"""
        payload = {"message": message, "priority": priority}
        if metadata:
            payload.update(metadata)
            
        thought = Thought(
            source="thought_bus_think",
            topic=topic,
            payload=payload
        )
        return self.publish(thought)

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        """
        topic supports:
          - exact match: "miner.signal"
          - prefix match with "*": "miner.*"
          - global: "*"
        """
        with self._lock:
            self._subs.setdefault(topic, []).append(handler)

    def list_subscribed_topics(self) -> List[str]:
        """Return the topic patterns that currently have at least one
        subscriber. Read-only introspection — used by BusFlightCheck to
        build the standing-wave topology without monkey-patching the
        bus."""
        with self._lock:
            return [t for t, handlers in self._subs.items() if handlers]

    def subscriber_count(self, topic: Optional[str] = None) -> int:
        """Count subscribers on a specific topic pattern, or across all
        patterns when topic is None."""
        with self._lock:
            if topic is None:
                return sum(len(h) for h in self._subs.values())
            return len(self._subs.get(topic, []))

    def publish(self, *args: Any, **kwargs: Any) -> Thought:
        thought = _coerce_thought_args(*args, **kwargs)
        with self._lock:
            self._memory.append(thought)
            self._persist(thought)
            handlers = self._match_handlers(thought.topic)

        for h in handlers:
            try:
                h(thought)
            except Exception as e:
                err = Thought(
                    source="thought_bus",
                    topic="system.error",
                    trace_id=thought.trace_id,
                    parent_id=thought.id,
                    payload={"error": str(e), "while_handling_topic": thought.topic},
                )
                with self._lock:
                    self._memory.append(err)
                    self._persist(err)

        return thought

    def get_recent(self, limit: int = 100) -> List[Json]:
        """Return recent thoughts for monitoring/telemetry use."""
        with self._lock:
            recent = list(self._memory)[-max(1, int(limit)) :]
        return [t.to_json() for t in recent]

    def publish_binary(
        self,
        *,
        source: str,
        topic: str,
        binary_payload: bytes,
        payload: Optional[Json] = None,
        meta: Optional[Json] = None,
    ) -> Thought:
        encoded = base64.b64encode(binary_payload).decode("ascii")
        thought = Thought(
            source=source,
            topic=topic,
            payload=payload or {},
            meta=meta or {},
            payload_encoding="binary",
            binary_payload_b64=encoded,
        )
        return self.publish(thought)

    def recall(self, topic_prefix: Optional[str] = None, limit: int = 100) -> List[Json]:
        with self._lock:
            items = list(self._memory)
        if topic_prefix:
            items = [t for t in items if t.topic.startswith(topic_prefix)]
        return [t.to_json() for t in items[-limit:]]

    def load_history_to_memory(self, jsonl_path: Optional[str] = None, topic_prefix: Optional[str] = None) -> int:
        """Hydrate the in-memory ring buffer from a persisted JSONL log.

        Unlike `replay()`, this does NOT call `publish()` and does NOT re-persist.
        It is safe to use at startup to restore context without triggering handlers
        or creating duplicate log lines.
        """
        path = jsonl_path or self._persist_path
        if not path or not os.path.exists(path):
            return 0

        loaded = 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    t = Thought(**data)
                    if topic_prefix and not t.topic.startswith(topic_prefix):
                        continue
                    with self._lock:
                        self._memory.append(t)
                    loaded += 1
        except Exception:
            return loaded

        return loaded

    def replay(self, jsonl_path: Optional[str] = None, topic_prefix: Optional[str] = None) -> int:
        path = jsonl_path or self._persist_path
        if not path or not os.path.exists(path):
            return 0

        count = 0
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                t = Thought(**data)
                if topic_prefix and not t.topic.startswith(topic_prefix):
                    continue
                self.publish(t)
                count += 1
        return count

    def _persist(self, thought: Thought) -> None:
        """Persist thought to JSONL with file locking for crash safety."""
        if not self._persist_path:
            return
        try:
            with open(self._persist_path, "a", encoding="utf-8") as f:
                # Acquire exclusive lock to prevent concurrent writes (cross-platform)
                _lock_file(f)
                try:
                    f.write(json.dumps(thought.to_json(), ensure_ascii=False) + "\n")
                    f.flush()
                    os.fsync(f.fileno())  # Ensure data hits disk
                finally:
                    _unlock_file(f)
        except (OSError, IOError) as e:
            # Log but don't crash on persistence failure
            pass

    def _match_handlers(self, topic: str) -> List[Subscriber]:
        with self._lock:
            handlers: List[Subscriber] = []
            for key, subs in self._subs.items():
                if key == "*":
                    handlers.extend(subs)
                elif key.endswith("*"):
                    prefix = key[:-1]
                    if topic.startswith(prefix):
                        handlers.extend(subs)
                else:
                    if key == topic:
                        handlers.extend(subs)
            return handlers


# ═══════════════════════════════════════════════════════════════
# GLOBAL SINGLETON & COMPATIBILITY
# ═══════════════════════════════════════════════════════════════

_thought_bus_instance: Optional[ThoughtBus] = None

def get_thought_bus(persist_path: Optional[str] = None) -> ThoughtBus:
    """Get or create the global ThoughtBus instance."""
    global _thought_bus_instance
    if _thought_bus_instance is None:
        _thought_bus_instance = ThoughtBus(
            persist_path=persist_path or "thoughts.jsonl"
        )
    return _thought_bus_instance

# Alias for compatibility - ThoughtSignal is just Thought
ThoughtSignal = Thought


# ─────────────────────────────────────────────────────────────────────────────
# Shape-agnostic accessors
# ─────────────────────────────────────────────────────────────────────────────
# subscribe() handlers receive a live ``Thought`` object, but get_recent()/recall()
# return ``to_json()`` DICTS. Readers that mixed these up (getattr on a dict) matched
# nothing silently. These helpers read topic/payload from either shape, so a single
# consumer works against both a subscription and the ring-buffer history.

def topic_of(thought: Any) -> str:
    """Return a thought's topic whether it's a Thought object or a to_json dict."""
    if isinstance(thought, dict):
        return str(thought.get("topic", "") or "")
    return str(getattr(thought, "topic", "") or "")


def payload_of(thought: Any) -> Dict[str, Any]:
    """Return a thought's payload whether it's a Thought object or a to_json dict."""
    if isinstance(thought, dict):
        val = thought.get("payload")
    else:
        val = getattr(thought, "payload", None)
    return val if isinstance(val, dict) else {}
