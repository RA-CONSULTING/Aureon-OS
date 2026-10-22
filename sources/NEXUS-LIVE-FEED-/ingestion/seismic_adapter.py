"""USGS seismic data ingestion module.

Fetches live seismic activity data from the United States Geological Survey
(USGS) API and normalises it into a simple Python data structure.

Metrics captured for each event:
    * magnitude
    * depth_km
    * latitude
    * longitude
    * timestamp (UTC ISO-8601)
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List
from urllib.request import urlopen

USGS_FEED_URL = (
    "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_hour.geojson"
)


@dataclass
class SeismicEvent:
    """Represents a single seismic event returned by the USGS feed."""

    magnitude: float
    depth_km: float
    latitude: float
    longitude: float
    timestamp: datetime


def fetch_recent_events(feed_url: str = USGS_FEED_URL) -> List[SeismicEvent]:
    """Retrieve recent earthquake events from the USGS feed.

    Args:
        feed_url: URL of the USGS GeoJSON feed. Defaults to the "all_hour" feed
            containing all earthquakes from the past hour.

    Returns:
        A list of :class:`SeismicEvent` objects.
    """

    with urlopen(feed_url, timeout=10) as response:  # nosec B310
        data = json.load(response)

    events: List[SeismicEvent] = []
    for feature in data.get("features", []):
        props = feature.get("properties", {})
        geom = feature.get("geometry", {})
        coords = geom.get("coordinates", [None, None, None])
        try:
            event = SeismicEvent(
                magnitude=props.get("mag"),
                depth_km=float(coords[2]),
                latitude=float(coords[1]),
                longitude=float(coords[0]),
                timestamp=datetime.fromtimestamp(props.get("time") / 1000, tz=timezone.utc),
            )
        except (TypeError, ValueError):
            # Skip malformed entries.
            continue
        events.append(event)

    return events


if __name__ == "__main__":
    for ev in fetch_recent_events()[:5]:
        print(
            {
                "magnitude": ev.magnitude,
                "depth_km": ev.depth_km,
                "latitude": ev.latitude,
                "longitude": ev.longitude,
                "timestamp": ev.timestamp.isoformat(),
            }
        )
