"use strict";

const HOLD_STATUS = Object.freeze({
  available: false,
  eligibleForAction: false,
  economicMutation: false,
  exitCode: 2,
  reason: "operational_route_unavailable",
  services: Object.freeze({}),
  started: Object.freeze([]),
  logs: Object.freeze({}),
});

class RuntimeManager {
  async ensureServices() {
    return HOLD_STATUS;
  }

  async inspectService() {
    return HOLD_STATUS;
  }

  async ensureService() {
    return HOLD_STATUS;
  }

  async stopService() {
    return false;
  }

  async restartService() {
    return HOLD_STATUS;
  }

  getLogPath() {
    return null;
  }

  async getStatus() {
    return HOLD_STATUS;
  }

  shutdown() {
    return false;
  }
}

module.exports = {
  RuntimeManager,
  WEB_URL: null,
  RUNTIME_URL: null,
  AUREON_URL: null,
  HOLD_STATUS,
};

if (require.main === module) {
  process.exitCode = 2;
}
