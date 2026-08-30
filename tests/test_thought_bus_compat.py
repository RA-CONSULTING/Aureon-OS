import unittest

import aureon.core.aureon_thought_bus as thought_bus_module
from aureon.core.aureon_thought_bus import Thought, ThoughtBus


class TestThoughtBusCompat(unittest.TestCase):
    def test_publish_accepts_topic_and_payload(self):
        bus = ThoughtBus()

        published = bus.publish("decisions.trading", {"symbol": "NATURALGAS", "side": "SELL"}, source="capital")

        self.assertIsInstance(published, Thought)
        self.assertEqual(published.topic, "decisions.trading")
        self.assertEqual(published.source, "capital")
        self.assertEqual(published.payload["symbol"], "NATURALGAS")

    def test_publish_accepts_dict_event(self):
        bus = ThoughtBus()

        published = bus.publish({"topic": "coordination.monitor", "source": "coordinator", "ready": True})

        self.assertEqual(published.topic, "coordination.monitor")
        self.assertEqual(published.source, "coordinator")
        self.assertTrue(published.payload["ready"])

    def test_publish_accepts_foreign_thought_like_object(self):
        class ForeignThought:
            def __init__(self):
                self.source = "whale_sonar"
                self.topic = "whale.sonar.BTCUSD"
                self.payload = {"code": "..."}
                self.meta = {"origin": "foreign"}
                self.trace_id = "trace-1"

        bus = ThoughtBus()

        published = bus.publish(ForeignThought())

        self.assertEqual(published.source, "whale_sonar")
        self.assertEqual(published.topic, "whale.sonar.BTCUSD")
        self.assertEqual(published.payload["code"], "...")
        self.assertEqual(published.meta["origin"], "foreign")


def test_singleton_honours_supported_environment_persist_path(tmp_path, monkeypatch):
    persist_path = tmp_path / "isolated-thoughts.jsonl"
    monkeypatch.setenv("AUREON_THOUGHT_BUS_PATH", str(persist_path))
    monkeypatch.setattr(thought_bus_module, "_thought_bus_instance", None)

    bus = thought_bus_module.get_thought_bus()
    bus.publish("test.isolated", {"safe": True}, source="test")

    assert persist_path.is_file()
    assert '"topic": "test.isolated"' in persist_path.read_text(encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
