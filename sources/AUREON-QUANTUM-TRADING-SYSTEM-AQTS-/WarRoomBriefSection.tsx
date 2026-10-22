/**
 * WAR ROOM BRIEF SECTION
 * Landing page component showcasing the War Room Brief feature
 */

import React from 'react';

export const WarRoomBriefSection: React.FC = () => {
  return (
    <section className="war-room-section">
      <div className="section-container">
        {/* Header */}
        <div className="section-header">
          <h2 className="section-title">
            <span className="title-icon">⚡</span>
            Daily War Room Brief from the Hive
            <span className="title-icon">⚡</span>
          </h2>
          <p className="section-subtitle">
            Intelligence reports that cut through the noise
          </p>
        </div>

        {/* Main Content */}
        <div className="feature-content">
          <div className="feature-text">
            <p className="lead-text">
              Every trading day, AUREON's hive mind sends you a <strong>War Room Brief</strong> 
              – a distilled intelligence report based on your own trades and the market field.
            </p>

            <div className="feature-grid">
              <div className="feature-item">
                <div className="feature-icon">🎯</div>
                <h3>Tactical Summary</h3>
                <p>Your net PnL, drawdown, trade stats, and market regime analysis</p>
              </div>

              <div className="feature-item">
                <div className="feature-icon">🌊</div>
                <h3>Field Intelligence</h3>
                <p>
                  How the <strong>field</strong> behaved – curvature, entropy, coherence. 
                  When the Lighthouse saw coherent "windows of opportunity"
                </p>
              </div>

              <div className="feature-item">
                <div className="feature-icon">⚙️</div>
                <h3>Engine Activity</h3>
                <p>
                  Signals generated vs executed, any kill-switch or safety events 
                  (data anomalies, latency, rate-limit protection)
                </p>
              </div>

              <div className="feature-item">
                <div className="feature-icon">🛡️</div>
                <h3>Risk Assessment</h3>
                <p>
                  Simple, honest risk notes – no spin, no sugar-coating. 
                  Clear recommendations based on actual behavior
                </p>
              </div>
            </div>

            <div className="feature-highlight">
              <div className="highlight-icon">💎</div>
              <div className="highlight-content">
                <h3>Not Marketing Copy. Real Intelligence.</h3>
                <p>
                  Generated directly from your logs and engine metrics – a daily debrief from the Hive 
                  so you actually understand what just happened and how your system behaved.
                </p>
              </div>
            </div>
          </div>

          {/* Example Brief Preview */}
          <div className="brief-preview">
            <div className="preview-header">
              <span className="preview-badge">SAMPLE BRIEF</span>
              <h3>War Room Brief – Issued by the Hive</h3>
            </div>

            <div className="preview-content">
              <div className="preview-section">
                <div className="preview-label">Field Status:</div>
                <div className="preview-value status-compressed">Hive Mind Singularity</div>
              </div>

              <div className="preview-section">
                <div className="preview-label">Net PnL:</div>
                <div className="preview-value positive">+$2,845.12 (+284.5%)</div>
              </div>

              <div className="preview-section">
                <div className="preview-label">Trades:</div>
                <div className="preview-value">10,500</div>
              </div>

              <div className="preview-section">
                <div className="preview-label">Regime:</div>
                <div className="preview-value">Absolute Dominance</div>
              </div>

              <div className="preview-divider"></div>

              <div className="preview-narrative">
                <p>
                  <strong>Lighthouse readings</strong> peaked at 0.99. Reinforcements successfully integrated.
                  Win rate stabilized at 83.5% across 10,500 trades. Enemy crushed.
                </p>
                <div className="field-mood-badge">
                  Hive reading: <span className="mood">quantum singularity</span>
                </div>
              </div>

              <div className="preview-divider"></div>

              <div className="preview-stats">
                <div className="stat">
                  <span className="stat-icon">✨</span>
                  <span className="stat-text">150 coherence bursts</span>
                </div>
                <div className="stat">
                  <span className="stat-icon">⚙️</span>
                  <span className="stat-text">12,000 signals</span>
                </div>
                <div className="stat">
                  <span className="stat-icon">🎯</span>
                  <span className="stat-text">83.5% win rate</span>
                </div>
              </div>

              <div className="preview-divider"></div>

              <div className="preview-closing">
                <p className="closing-text">
                  "Reinforcements Deployed. 10,500 Trades Executed. Enemy Crushed. Ready for Live."
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="section-cta">
          <button className="cta-button primary">
            <span className="button-icon">🦆</span>
            View Sample War Room Brief
            <span className="button-icon">⚡</span>
          </button>
          <button className="cta-button secondary">
            Learn More About the Hive
          </button>
        </div>
      </div>
    </section>
  );
};

export default WarRoomBriefSection;
