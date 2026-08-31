"""
Shape Outcome ML Training Pipeline

Collects labeled whale shape examples from Elephant Memory and trains
a lightweight classifier to replace heuristics with learned patterns.

Architecture:
- Extract features from shape spectrograms + orderbook context
- Label: subtype, win/loss, profit
- Model: Random Forest (fast, interpretable) or XGBoost
- Training: Incremental learning as new outcomes arrive
- Deployment: Replace _classify_shape() heuristics

Features:
- Spectrogram: centroid, bandwidth, flatness, peak_count, energy
- Orderbook: layering_score, depth_imbalance, wall_count
- Harmonic: dominant_frequency, coherence, phase_alignment
- Context: volatility, volume, time_of_day

Target: Predict (shape_subtype, expected_profit, win_probability)
"""
from aureon.core.aureon_baton_link import link_system as _baton_link; _baton_link(__name__)
import sys
import os

if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    try:
        import io
        def _is_utf8_wrapper(stream):
            return (isinstance(stream, io.TextIOWrapper) and 
                    hasattr(stream, 'encoding') and stream.encoding and
                    stream.encoding.lower().replace('-', '') == 'utf8')
        if hasattr(sys.stdout, 'buffer') and not _is_utf8_wrapper(sys.stdout):
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
        # Skip stderr wrapping (causes Windows exit errors)
    except Exception:
        pass

import logging
import numpy as np
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Try to import ML libraries
try:
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import classification_report, mean_squared_error, accuracy_score
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available; ML training disabled")

# Try to import elephant memory
try:
    from aureon.intelligence.aureon_elephant_learning import ElephantMemory
    ELEPHANT_AVAILABLE = True
except ImportError:
    ELEPHANT_AVAILABLE = False
    logger.warning("Elephant Memory not available")


@dataclass
class ShapeFeatures:
    """Features extracted from a shape detection event"""
    # Spectrogram features
    spectral_centroid: float
    spectral_bandwidth: float
    spectral_flatness: float
    spectral_energy: float
    peak_count: int
    
    # Orderbook features
    layering_score: float
    depth_imbalance: float  # (bids - asks) / (bids + asks)
    wall_count: int
    
    # Harmonic features
    dominant_frequency: float
    harmonic_coherence: float
    phase_alignment: float
    
    # Context features
    volatility: float
    volume: float
    hour_of_day: int
    
    # Label (if known)
    shape_subtype: str = 'unknown'
    is_win: Optional[bool] = None
    profit: Optional[float] = None
    
    def to_feature_vector(self) -> np.ndarray:
        """Convert to numpy array for ML"""
        return np.array([
            self.spectral_centroid,
            self.spectral_bandwidth,
            self.spectral_flatness,
            self.spectral_energy,
            float(self.peak_count),
            self.layering_score,
            self.depth_imbalance,
            float(self.wall_count),
            self.dominant_frequency,
            self.harmonic_coherence,
            self.phase_alignment,
            self.volatility,
            self.volume,
            float(self.hour_of_day),
        ])
    
    @staticmethod
    def feature_names() -> List[str]:
        return [
            'spectral_centroid', 'spectral_bandwidth', 'spectral_flatness', 'spectral_energy',
            'peak_count', 'layering_score', 'depth_imbalance', 'wall_count',
            'dominant_frequency', 'harmonic_coherence', 'phase_alignment',
            'volatility', 'volume', 'hour_of_day'
        ]


class ShapeOutcomeTrainer:
    """Train and manage shape outcome models"""
    
    def __init__(self, model_dir: str = "whale_shape_models"):
        self.model_dir = Path(model_dir)
        self.model_dir.mkdir(exist_ok=True)
        
        # Models
        self.subtype_classifier: Optional[RandomForestClassifier] = None
        self.profit_regressor: Optional[RandomForestRegressor] = None
        self.win_classifier: Optional[RandomForestClassifier] = None
        
        # Training data cache
        self.training_data: List[ShapeFeatures] = []
        
        # Load existing models if available
        self._load_models()
    
    def _load_models(self):
        """Refuse executable pickle model artifacts.

        Scikit-learn pickle/joblib files can execute attacker-controlled code
        during deserialization. Models therefore remain in memory until a
        schema-bound non-executable format (for example, a reviewed ONNX or
        skops contract) is implemented.
        """

        legacy = tuple(self.model_dir.glob("*.pkl"))
        if legacy:
            logger.warning(
                "Model persistence HOLD: %d legacy pickle artifact(s) ignored",
                len(legacy),
            )
    
    def _save_models(self):
        """Keep trained models in memory; never emit executable pickle data."""

        logger.warning(
            "Model persistence HOLD: executable pickle/joblib output is disabled"
        )
    
    def collect_training_data_from_elephant(self, min_samples: int = 50) -> int:
        """
        Extract labeled shape examples from Elephant Memory.
        
        Returns:
            Number of samples collected
        """
        if not ELEPHANT_AVAILABLE:
            logger.warning("Elephant Memory not available")
            return 0
        
        try:
            elephant = ElephantMemory()
            patterns = elephant.get_patterns(pattern_type='whale_shape')
            
            collected = 0
            for pattern in patterns:
                # Extract features from pattern conditions
                conditions = pattern.conditions or {}
                spectrogram = conditions.get('spectrogram', {})
                
                # Only use patterns with outcomes
                if pattern.total_occurrences == 0:
                    continue
                
                # Create feature object
                features = ShapeFeatures(
                    spectral_centroid=float(spectrogram.get('centroid', 0.0)),
                    spectral_bandwidth=float(spectrogram.get('bandwidth', 0.0)),
                    spectral_flatness=float(spectrogram.get('flatness', 0.0)),
                    spectral_energy=float(spectrogram.get('energy', 0.0)),
                    peak_count=len(spectrogram.get('peaks', [])),
                    layering_score=float(conditions.get('layering_score', 0.0)),
                    depth_imbalance=float(conditions.get('depth_imbalance', 0.0)),
                    wall_count=len(conditions.get('walls', [])),
                    dominant_frequency=float(spectrogram.get('harmonic', {}).get('dominant_freq', 0.0)),
                    harmonic_coherence=float(spectrogram.get('harmonic', {}).get('coherence', 0.0)),
                    phase_alignment=float(spectrogram.get('harmonic', {}).get('phase_alignment', 0.0)),
                    volatility=float(conditions.get('volatility', 0.0)),
                    volume=float(conditions.get('volume', 0.0)),
                    hour_of_day=int(conditions.get('hour_of_day', 12)),
                    shape_subtype=pattern.symbol.split(':')[1] if ':' in pattern.symbol else 'unknown',
                    is_win=(pattern.win_rate > 0.5) if pattern.total_occurrences > 0 else None,
                    profit=pattern.profit_factor if pattern.total_occurrences > 0 else None
                )
                
                self.training_data.append(features)
                collected += 1
            
            logger.info(f"📊 Collected {collected} labeled shape examples from Elephant Memory")
            return collected
        
        except Exception as e:
            logger.error(f"Failed to collect training data: {e}", exc_info=True)
            return 0
    
    def train(self, test_size: float = 0.2, min_samples: int = 50):
        """
        Train all models on collected data.
        
        Args:
            test_size: Fraction of data to hold out for testing
            min_samples: Minimum samples required to train
        """
        if not SKLEARN_AVAILABLE:
            logger.error("scikit-learn not available; cannot train")
            return
        
        if len(self.training_data) < min_samples:
            logger.warning(f"Insufficient training data: {len(self.training_data)} < {min_samples}")
            return
        
        # Prepare feature matrix
        X = np.array([f.to_feature_vector() for f in self.training_data])
        
        # Prepare labels
        y_subtype = np.array([f.shape_subtype for f in self.training_data])
        y_win = np.array([int(f.is_win) if f.is_win is not None else -1 for f in self.training_data])
        y_profit = np.array([f.profit if f.profit is not None else 0.0 for f in self.training_data])
        
        # Filter out unlabeled samples
        labeled_win = y_win >= 0
        X_win = X[labeled_win]
        y_win = y_win[labeled_win]
        
        labeled_profit = y_profit != 0.0
        X_profit = X[labeled_profit]
        y_profit = y_profit[labeled_profit]
        
        logger.info(f"🎯 Training with {len(X)} total samples, {len(X_win)} with win labels, {len(X_profit)} with profit labels")
        
        # Train subtype classifier
        if len(np.unique(y_subtype)) > 1:
            X_train, X_test, y_train, y_test = train_test_split(X, y_subtype, test_size=test_size, random_state=42)
            self.subtype_classifier = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
            self.subtype_classifier.fit(X_train, y_train)
            
            y_pred = self.subtype_classifier.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            logger.info(f"📈 Subtype classifier accuracy: {acc:.3f}")
            logger.info(f"\n{classification_report(y_test, y_pred, zero_division=0)}")
        
        # Train win classifier
        if len(X_win) >= min_samples and len(np.unique(y_win)) > 1:
            X_train, X_test, y_train, y_test = train_test_split(X_win, y_win, test_size=test_size, random_state=42)
            self.win_classifier = RandomForestClassifier(n_estimators=100, max_depth=8, random_state=42)
            self.win_classifier.fit(X_train, y_train)
            
            y_pred = self.win_classifier.predict(X_test)
            acc = accuracy_score(y_test, y_pred)
            logger.info(f"📈 Win classifier accuracy: {acc:.3f}")
        
        # Train profit regressor
        if len(X_profit) >= min_samples:
            X_train, X_test, y_train, y_test = train_test_split(X_profit, y_profit, test_size=test_size, random_state=42)
            self.profit_regressor = RandomForestRegressor(n_estimators=100, max_depth=8, random_state=42)
            self.profit_regressor.fit(X_train, y_train)
            
            y_pred = self.profit_regressor.predict(X_test)
            rmse = np.sqrt(mean_squared_error(y_test, y_pred))
            logger.info(f"📈 Profit regressor RMSE: {rmse:.2f}")
        
        # Save models
        self._save_models()
    
    def predict(self, features: ShapeFeatures) -> Dict[str, Any]:
        """
        Predict shape subtype, win probability, and expected profit.
        
        Returns:
            Dict with predictions
        """
        if not SKLEARN_AVAILABLE:
            return {'error': 'sklearn not available'}
        
        X = features.to_feature_vector().reshape(1, -1)
        result = {}
        
        try:
            if self.subtype_classifier:
                subtype = self.subtype_classifier.predict(X)[0]
                subtype_proba = self.subtype_classifier.predict_proba(X)[0]
                result['predicted_subtype'] = subtype
                result['subtype_confidence'] = float(np.max(subtype_proba))
            
            if self.win_classifier:
                win_proba = self.win_classifier.predict_proba(X)[0]
                result['win_probability'] = float(win_proba[1]) if len(win_proba) > 1 else 0.5
            
            if self.profit_regressor:
                profit = self.profit_regressor.predict(X)[0]
                result['expected_profit'] = float(profit)
        
        except Exception as e:
            logger.error(f"Prediction error: {e}")
            result['error'] = str(e)
        
        return result
    
    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained models"""
        if not self.subtype_classifier:
            return {}
        
        feature_names = ShapeFeatures.feature_names()
        importances = self.subtype_classifier.feature_importances_
        
        return dict(zip(feature_names, importances))


# Global trainer instance
_trainer: Optional[ShapeOutcomeTrainer] = None

def get_trainer() -> ShapeOutcomeTrainer:
    """Get singleton trainer"""
    global _trainer
    if _trainer is None:
        _trainer = ShapeOutcomeTrainer()
    return _trainer


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    print("🤖 Whale Shape Outcome ML Training Pipeline\n")
    
    trainer = get_trainer()
    
    # Collect training data
    print("📊 Collecting training data from Elephant Memory...")
    n_samples = trainer.collect_training_data_from_elephant(min_samples=10)
    print(f"   Collected {n_samples} samples\n")
    
    if n_samples >= 10:
        # Train models
        print("🎯 Training models...")
        trainer.train(test_size=0.2, min_samples=10)
        
        # Show feature importance
        print("\n📈 Feature Importance:")
        importance = trainer.get_feature_importance()
        for feat, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True)[:5]:
            print(f"   {feat}: {imp:.3f}")
        
        print("\n✅ Training complete! Models saved to whale_shape_models/")
    else:
        print("⚠️  Not enough labeled data to train. Need at least 10 samples with outcomes.")
        print("   Run the whale detection system and record outcomes to build training data.")
