const assert = require('assert');
const { childSafetySystem } = require('../childSafety');

const report = childSafetySystem.monitorMessage('u1', 'This causes hurt and pain');
assert.strictEqual(report.harmful, true);
assert.strictEqual(childSafetySystem.getReports().length, 1);
console.log('childSafety tests passed.');
