import { AureonDataPoint, CoherenceDataPoint } from './types';
import { AQTSOrchestrator } from './core/aqtsOrchestrator';

const DATA_INTERVAL_MS = 150;

// This service simulates a live WebSocket connection by generating and pushing data.
interface WebSocketCallbacks {
  onOpen: () => void;
  onMessage: (data: { aureon: AureonDataPoint, nexus: CoherenceDataPoint }) => void;
  onError: (error: Error) => void;
  onClose: () => void;
}

export const connectWebSocket = (callbacks: WebSocketCallbacks) => {
  const orchestrator = new AQTSOrchestrator();

  // Simulate async connection
  setTimeout(() => {
    callbacks.onOpen();
  }, 500);

  const intervalId = setInterval(() => {
    try {
      const output = orchestrator.next();
      callbacks.onMessage({ aureon: output.aureonPoint, nexus: output.nexusPoint });
    } catch (error) {
      callbacks.onError(error as Error);
      clearInterval(intervalId);
    }
  }, DATA_INTERVAL_MS);

  return {
    close: () => {
      clearInterval(intervalId);
      callbacks.onClose();
    }
  };
};
