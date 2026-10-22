
import asyncio
import unittest
from unittest.mock import patch, AsyncMock, ANY

from routers import qssr

class TestQSSR(unittest.IsolatedAsyncioTestCase):

    @patch('routers.qssr.recorder.start', new_callable=AsyncMock)
    @patch('routers.qssr.recorder.record_time_series', new_callable=AsyncMock)
    async def test_ticker_records_time_series(self, mock_record_time_series, mock_start):
        """
        Test that the ticker function calls record_time_series.
        """
        # Run the ticker for a very short time to get one or two readings
        ticker_task = asyncio.create_task(qssr.ticker())
        await asyncio.sleep(qssr.TICK_SECONDS + 0.1)
        ticker_task.cancel()
        try:
            await ticker_task
        except asyncio.CancelledError:
            pass # Task cancellation is expected

        # Verify that start was called
        mock_start.assert_called_once()

        # Verify that record_time_series was called at least once with the correct arguments
        mock_record_time_series.assert_any_await(
            measurement="solar_coherence",
            value=ANY,
            tags={"source": "QSSR_v2"}
        )

if __name__ == "__main__":
    unittest.main()
