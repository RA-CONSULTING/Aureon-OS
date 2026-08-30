import aureon.core.metrics as metrics


def test_api_429_counter_increments_from_current_value() -> None:
    labels = {"exchange": "testex", "endpoint": "testpath"}
    before = metrics.get_metric_value(metrics.api_429_counter, **labels)

    metrics.api_429_counter.inc(1, **labels)

    assert metrics.get_metric_value(metrics.api_429_counter, **labels) == before + 1.0
