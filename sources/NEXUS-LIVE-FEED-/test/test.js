const assert = require('assert');
const { metrics, sampleMetrics } = require('../src/metrics');
const { findAndTargetStorm } = require('../src/stormTargeting');

async function run() {
  // Ensure each metric has description and unit
  for (const [name, meta] of Object.entries(metrics)) {
    assert.ok(meta.description, `${name} missing description`);
    assert.ok(meta.unit, `${name} missing unit`);
  }

  // Ensure sampleMetrics returns values for all metrics
  const sample = sampleMetrics();
  assert.ok(sample.timestamp, 'timestamp missing');
  for (const name of Object.keys(metrics)) {
    assert.ok(sample.metrics[name], `missing metric ${name}`);
    assert.strictEqual(typeof sample.metrics[name].value, 'number', 'value should be number');
  }

  // Test storm targeting with mock fetch
  const mockFetch = async () => ({
    json: async () => ({
      features: [
        { id: '1', properties: { severity: 'Moderate', headline: 'Storm A', event: 'Rain' } },
        { id: '2', properties: { severity: 'Severe', headline: 'Storm B', event: 'Wind' } }
      ]
    })
  });
  const storm = await findAndTargetStorm(mockFetch);
  assert.strictEqual(storm.headline, 'Storm B');
  assert.strictEqual(storm.severity, 'Severe');

  console.log('All tests passed.');
}

run();
