
import unittest
import asyncio
import json
import hashlib
from unittest.mock import patch, AsyncMock

from core.chronicle_recorder import ChronicleRecorder

class TestChronicleRecorder(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.recorder = ChronicleRecorder()
        # Allow tasks to start
        await asyncio.sleep(0)

    async def asyncTearDown(self):
        await self.recorder.shutdown()

    def test_generate_checksum(self):
        """
        Test the checksum generation logic for correctness.
        """
        data = {"message": "Hello, world!", "id": 123}
        dhash = hashlib.sha256()
        encoded = json.dumps(data, sort_keys=True).encode()
        dhash.update(encoded)
        expected_checksum = dhash.hexdigest()

        self.assertEqual(self.recorder._generate_checksum(data), expected_checksum)

    async def test_record_event(self):
        """
        Test that `record_event` correctly puts the event onto the asyncio Queue.
        """
        self.recorder._queue.put = AsyncMock()
        
        event_type = "TEST_EVENT"
        details = {"data": "some_data"}
        
        await self.recorder.record_event(event_type, details)
        
        self.recorder._queue.put.assert_awaited_once_with(("event", details, {"event_type": event_type}))

    @patch('core.chronicle_recorder.event_logger')
    async def test_process_queue_processes_event(self, mock_event_logger):
        """
        Test that the _process_queue correctly processes an event from the queue and logs it.
        """
        event_type = "UNIT_TEST_EVENT"
        data = {"payload": "test_data"}
        
        await self.recorder.record_event(event_type, data)
        
        # Allow the loop to process the event
        await asyncio.sleep(0.1)

        mock_event_logger.info.assert_called_once()
        logged_call = mock_event_logger.info.call_args[0][0]
        logged_data = json.loads(logged_call)

        self.assertEqual(logged_data['event_type'], event_type)
        self.assertEqual(logged_data['details'], data)

if __name__ == "__main__":
    unittest.main()
