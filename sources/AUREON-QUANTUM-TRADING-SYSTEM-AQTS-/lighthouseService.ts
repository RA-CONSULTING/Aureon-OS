
import { CoherenceDataPoint, DejaVuEvent, HistoricalDataPoint, NexusAnalysisResult } from './types';

const PATTERN_LENGTH = 4;
const SIMILARITY_THRESHOLD = 0.005; // Sum of squared differences for a pattern match
const SEARCH_BACK_DISTANCE = 60;  // How many steps back to search for a match
const COOLDOWN_PERIOD = 15;       // Minimum steps between detected events

// This function now analyzes the real-time coherence data stream for Déjà Vu events
export const runAnalysis = (
    realtimeData: CoherenceDataPoint[], 
    historicalData: HistoricalDataPoint[]
): Omit<NexusAnalysisResult, 'report' | 'aureonData' | 'monitoringEvents'> => {

  const dejaVuEvents: DejaVuEvent[] = [];
  let lastEventTime = -Infinity;

  if (realtimeData.length >= PATTERN_LENGTH + 1) {
    // Iterate through the data, looking for repeating patterns
    for (let i = PATTERN_LENGTH; i < realtimeData.length - PATTERN_LENGTH; i++) {
        if (realtimeData[i].time < lastEventTime + COOLDOWN_PERIOD) continue;

        const currentPattern = realtimeData.slice(i, i + PATTERN_LENGTH).map(p => p.cognitiveCapacity);

        // Search for a matching pattern in the recent past
        const searchStart = Math.max(0, i - SEARCH_BACK_DISTANCE);
        for (let j = searchStart; j < i - PATTERN_LENGTH; j++) {
            const pastPattern = realtimeData.slice(j, j + PATTERN_LENGTH).map(p => p.cognitiveCapacity);

            // Calculate sum of squared differences to find a match
            const diff = currentPattern.reduce((sum, val, k) => sum + Math.pow(val - pastPattern[k], 2), 0);

            if (diff < SIMILARITY_THRESHOLD) {
                // To avoid clustering, check if this is a new event
                if (realtimeData[i].time > lastEventTime + COOLDOWN_PERIOD) {
                    dejaVuEvents.push({ time: realtimeData[i].time, intensity: realtimeData[i].cognitiveCapacity });
                    lastEventTime = realtimeData[i].time;
                }
                break; 
            }
        }
    }
  }


  return { realtimeData, historicalData, dejaVuEvents };
};


// This function is now repurposed to provide the historical data for the chart.
// The term "Backtest" is kept to minimize changes in App.tsx, but it now represents a historical simulation.
export const runBacktest = (historicalData: HistoricalDataPoint[]) => {
    // FIX: Add a guard to ensure historicalData is an array before mapping.
    // This prevents a crash if nexusResult is in an inconsistent state during a render.
    if (!Array.isArray(historicalData)) {
        return {
            performanceData: [],
            metrics: {
                finalReturn: 0,
                sharpeRatio: 0
            }
        };
    }
    return {
        performanceData: historicalData.map(d => ({
            time: d.year,
            cumulativeReturn: d.cognitiveCapacity
        })),
        metrics: {
            finalReturn: historicalData.length > 0 ? historicalData[historicalData.length - 1].cognitiveCapacity : 0,
            sharpeRatio: 0 // Not applicable in this context
        }
    }
}
