import React, { useCallback, useState } from 'react';
import LandingPage from './LandingPage';
import TradingConsole from './TradingConsole';

const App: React.FC = () => {
  const [view, setView] = useState<'landing' | 'console'>('landing');

  const handleStartTrading = useCallback(() => setView('console'), []);
  const handleReturnToLanding = useCallback(() => setView('landing'), []);

  return view === 'landing' ? (
    <LandingPage onStartTrading={handleStartTrading} />
  ) : (
    <TradingConsole onBackToLanding={handleReturnToLanding} />
  );
};

export default App;
