export async function findAndTargetStorm(fetchImpl = fetch) {
  // Fetch storm data using provided fetch implementation
  const response = await fetchImpl();
  const data = await response.json();
  const features = Array.isArray(data.features) ? data.features : [];

  // Map severity labels to numeric priority
  const severityRank = {
    Unknown: 0,
    Minor: 1,
    Moderate: 2,
    Severe: 3,
    Extreme: 4
  };

  // Select the storm with the highest severity
  let target = null;
  for (const feature of features) {
    const props = feature.properties || {};
    if (
      !target ||
      (severityRank[props.severity] || 0) > (severityRank[target.severity] || 0)
    ) {
      target = {
        id: feature.id,
        headline: props.headline,
        severity: props.severity,
        event: props.event
      };
    }
  }

  return target;
}

