/**
 * WAR ROOM BRIEF COMPONENT
 * 
 * Displays daily intelligence from the AUREON Hive
 * Super Quantum Quackers General reporting for duty 🦆⚡
 */

import React, { useState, useEffect } from 'react';
import { WarRoomBrief } from '../core/hiveWarRoomReport';
import sampleBriefData from './sample_war_room_brief.json';

interface WarRoomBriefProps {
  brief?: WarRoomBrief;
  autoLoad?: boolean;
}

export const WarRoomBriefComponent: React.FC<WarRoomBriefProps> = ({ 
  brief: propBrief,
  autoLoad = false 
}) => {
  const [brief, setBrief] = useState<WarRoomBrief | null>(propBrief || null);
  const [loading, setLoading] = useState(autoLoad && !propBrief);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (autoLoad && !propBrief) {
      loadBrief();
    }
  }, [autoLoad, propBrief]);

  const loadBrief = async () => {
    try {
      setLoading(true);
      // Try to fetch from API first
      try {
        const response = await fetch('/api/war-room-brief');
        if (response.ok) {
            const data = await response.json();
            setBrief(data);
            setError(null);
            return;
        }
      } catch (e) {
        console.warn("API fetch failed, falling back to sample data", e);
      }
      
      // Fallback to sample data (casted to WarRoomBrief as JSON import might be loose)
      setBrief(sampleBriefData as unknown as WarRoomBrief);
      setError(null);

    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="war-room-brief loading">
        <div className="hive-loader">
          <div className="quantum-spinner"></div>
          <p>Hive compiling intelligence...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="war-room-brief error">
        <div className="error-panel">
          <h3>⚠️ Hive Connection Error</h3>
          <p>{error}</p>
          <button onClick={loadBrief}>Retry</button>
        </div>
      </div>
    );
  }

  if (!brief) {
    return null;
  }

  const { fieldIntelligence: fi, engineActivity: ea, tradeBreakdown: tb, riskAssessment: ra } = brief;
  const winRate = brief.totalTrades > 0 ? ((tb.wins / brief.totalTrades) * 100).toFixed(1) : '0';

  return (
    <div className="war-room-brief">
      {/* Header */}
      <div className="brief-header">
        <div className="header-glow"></div>
        <h1>
          <span className="quantum-icon">⚡</span>
          WAR ROOM BRIEF
          <span className="quantum-icon">⚡</span>
        </h1>
        <p className="subtitle">Issued by the Hive</p>
        
        <div className="header-info">
          <div className="info-item">
            <span className="label">Date:</span>
            <span className="value">{brief.date}</span>
          </div>
          <div className="info-item">
            <span className="label">User:</span>
            <span className="value">{brief.user}</span>
          </div>
          <div className="info-item">
            <span className="label">Bot:</span>
            <span className="value">{brief.botName}</span>
          </div>
          <div className="info-item field-status">
            <span className="label">Field Status:</span>
            <span className={`status-badge ${brief.fieldStatus.toLowerCase()}`}>
              {brief.fieldStatus}
            </span>
          </div>
        </div>
      </div>

      {/* Tactical Summary */}
      <section className="brief-section tactical-summary">
        <h2>
          <span className="section-icon">🎯</span>
          Tactical Summary
        </h2>
        
        <div className="summary-grid">
          <div className="summary-card pnl">
            <div className="card-label">Net PnL</div>
            <div className={`card-value ${brief.netPnL >= 0 ? 'positive' : 'negative'}`}>
              {brief.netPnL >= 0 ? '+' : ''}${brief.netPnL.toFixed(2)}
              <span className="percentage">
                ({brief.netPnLPercent >= 0 ? '+' : ''}{brief.netPnLPercent.toFixed(2)}%)
              </span>
            </div>
          </div>

          <div className="summary-card">
            <div className="card-label">Trades</div>
            <div className="card-value">{brief.totalTrades}</div>
          </div>

          <div className="summary-card">
            <div className="card-label">Max Drawdown</div>
            <div className={`card-value ${brief.maxDrawdown > 10 ? 'warning' : ''}`}>
              {brief.maxDrawdown.toFixed(2)}%
            </div>
          </div>

          <div className="summary-card">
            <div className="card-label">Regime</div>
            <div className="card-value regime">{brief.regime}</div>
          </div>
        </div>

        <div className="field-summary">
          Today the field leaned <strong>{brief.marketBias}</strong> with{' '}
          <strong className={`coherence-${brief.coherenceLevel}`}>{brief.coherenceLevel}</strong> coherence.
        </div>
      </section>

      {/* Field Intelligence */}
      <section className="brief-section field-intelligence">
        <h2>
          <span className="section-icon">🌊</span>
          Field Intelligence <span className="quantum-vibes">(Quantum Vibes)</span>
        </h2>

        <div className="intelligence-grid">
          <div className="intel-card lighthouse">
            <div className="card-header">
              <span className="icon">🔦</span>
              <span className="title">Lighthouse Intensity</span>
            </div>
            <div className="intensity-bar">
              <div 
                className="intensity-fill" 
                style={{ width: `${fi.averageLighthouseIntensity * 100}%` }}
              />
              <span className="intensity-value">{fi.averageLighthouseIntensity.toFixed(3)}</span>
            </div>
          </div>

          <div className="intel-card coherence">
            <div className="card-header">
              <span className="icon">✨</span>
              <span className="title">Coherence Bursts</span>
            </div>
            <div className="coherence-count">{fi.coherenceBursts}</div>
            <div className="burst-indicator">
              {Array.from({ length: Math.min(fi.coherenceBursts, 10) }).map((_, i) => (
                <span key={i} className="burst-dot" style={{ animationDelay: `${i * 0.1}s` }}></span>
              ))}
            </div>
          </div>

          <div className="intel-card entropy">
            <div className="card-header">
              <span className="icon">📊</span>
              <span className="title">Entropy Trend</span>
            </div>
            <div className={`entropy-status ${fi.entropyTrend}`}>
              {fi.entropyTrend === 'falling' && '↓ Falling'}
              {fi.entropyTrend === 'rising' && '↑ Rising'}
              {fi.entropyTrend === 'stable' && '→ Stable'}
            </div>
          </div>

          <div className="intel-card peak">
            <div className="card-header">
              <span className="icon">⚡</span>
              <span className="title">Peak Coherence</span>
            </div>
            <div className="peak-value">{fi.peakCoherenceValue.toFixed(3)}</div>
            <div className="peak-time">{fi.peakCoherenceTime}</div>
          </div>
        </div>

        <div className="field-narrative">
          <p>
            Lighthouse readings peaked at <strong>{fi.peakCoherenceValue.toFixed(2)}</strong> during{' '}
            <strong>{fi.peakCoherenceTime}</strong>.
            {fi.entropyTrend === 'falling' && 
              ' Entropy fell, suggesting a transition from noise to order.'
            }
            {fi.entropyTrend === 'rising' && 
              ' Entropy rose, indicating increasing market chaos.'
            }
            {fi.entropyTrend === 'stable' && 
              ' Entropy remained stable throughout the session.'
            }
          </p>
          <div className="field-mood">
            <span className="mood-label">Hive reading:</span>
            <span className={`mood-badge ${fi.fieldMood.replace(/\s+/g, '-')}`}>
              {fi.fieldMood}
            </span>
          </div>
        </div>
      </section>

      {/* Engine Activity */}
      <section className="brief-section engine-activity">
        <h2>
          <span className="section-icon">⚙️</span>
          Engine Activity
        </h2>

        <div className="activity-stats">
          <div className="stat-row signals">
            <span className="stat-label">Signals:</span>
            <span className="stat-value">
              {ea.signalsGenerated} generated, {ea.signalsExecuted} executed
            </span>
            <div className="execution-rate">
              Execution Rate: {ea.signalsGenerated > 0 
                ? ((ea.signalsExecuted / ea.signalsGenerated) * 100).toFixed(0) 
                : '0'}%
            </div>
          </div>

          {ea.rateLimitEvents > 0 && (
            <div className="stat-row warning">
              <span className="stat-icon">⚠️</span>
              <span className="stat-value">Rate-limit events: {ea.rateLimitEvents}</span>
            </div>
          )}

          {ea.killSwitchEvents > 0 ? (
            <div className="stat-row alert">
              <span className="stat-icon">🛑</span>
              <span className="stat-value">
                Kill-switch engaged {ea.killSwitchEvents} time(s) for {ea.killSwitchDuration} minutes total
              </span>
            </div>
          ) : (
            <div className="stat-row success">
              <span className="stat-icon">✅</span>
              <span className="stat-value">No kill-switch events</span>
            </div>
          )}

          {ea.dataLatencySpikes > 0 && (
            <div className="stat-row warning">
              <span className="stat-icon">📡</span>
              <span className="stat-value">Data latency spikes: {ea.dataLatencySpikes}</span>
            </div>
          )}
        </div>
      </section>

      {/* Performance Breakdown */}
      <section className="brief-section performance-breakdown">
        <h2>
          <span className="section-icon">📈</span>
          Performance Breakdown
        </h2>

        <div className="performance-grid">
          <div className="perf-card win-rate">
            <div className="perf-label">Win Rate</div>
            <div className="perf-value">{winRate}%</div>
            <div className="perf-detail">{tb.wins}W / {tb.losses}L</div>
          </div>

          <div className="perf-card rr">
            <div className="perf-label">Average R:R</div>
            <div className="perf-value">{tb.averageRR.toFixed(2)}</div>
          </div>

          <div className="perf-card winner">
            <div className="perf-label">Biggest Winner</div>
            <div className="perf-symbol">{tb.biggestWinner.pair}</div>
            <div className="perf-value positive">+${tb.biggestWinner.pnl.toFixed(2)}</div>
          </div>

          <div className="perf-card loser">
            <div className="perf-label">Biggest Loser</div>
            <div className="perf-symbol">{tb.biggestLoser.pair}</div>
            <div className="perf-value negative">${tb.biggestLoser.pnl.toFixed(2)}</div>
          </div>
        </div>

        <div className="top-pairs">
          <h3>Top Pairs</h3>
          <div className="pairs-list">
            {tb.topPairs.map((pair, idx) => (
              <div key={idx} className="pair-row">
                <span className="pair-rank">#{idx + 1}</span>
                <span className="pair-symbol">{pair.pair}</span>
                <span className={`pair-pnl ${pair.pnl >= 0 ? 'positive' : 'negative'}`}>
                  {pair.pnl >= 0 ? '+' : ''}${pair.pnl.toFixed(2)}
                </span>
                <span className="pair-trades">{pair.trades} trades</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Risk & Recommendations */}
      <section className="brief-section risk-assessment">
        <h2>
          <span className="section-icon">🛡️</span>
          Risk & Recommendations
        </h2>

        <div className="risk-grid">
          <div className={`risk-card drawdown ${ra.drawdownStatus.replace(/\s+/g, '-')}`}>
            <div className="risk-label">Drawdown Status</div>
            <div className="risk-value">{ra.drawdownStatus}</div>
          </div>

          <div className={`risk-card volatility ${ra.volatilityLevel}`}>
            <div className="risk-label">Volatility Level</div>
            <div className="risk-value">{ra.volatilityLevel}</div>
          </div>
        </div>

        <div className="recommendations">
          <h3>Recommendations</h3>
          <ul className="recommendation-list">
            {ra.recommendations.map((rec, idx) => (
              <li key={idx} className="recommendation-item">
                <span className="bullet">•</span>
                <span className="text">{rec}</span>
              </li>
            ))}
          </ul>
        </div>
      </section>

      {/* Closing */}
      <section className="brief-section closing">
        <div className="closing-message">{brief.closingMessage}</div>
        <div className="hive-status">
          <span className="status-label">Hive Status:</span>
          <span className={`status-indicator ${brief.hiveStatus}`}>
            {brief.hiveStatus.toUpperCase()}
          </span>
        </div>
        <div className="brief-footer">
          <span className="footer-icon">⚡</span>
          End of War Room Brief
          <span className="footer-icon">⚡</span>
        </div>
      </section>
    </div>
  );
};

export default WarRoomBriefComponent;
