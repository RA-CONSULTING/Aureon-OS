import React, { useEffect, useState } from 'react';
import { MonitoringEvent } from './types';

interface TradeNotificationProps {
  trade: MonitoringEvent;
}

const TradeNotification: React.FC<TradeNotificationProps> = ({ trade }) => {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    // This timeout is to ensure the component is mounted before starting the transition
    const enterTimeout = setTimeout(() => setVisible(true), 50);
    // This timeout starts the fade-out animation before the component is unmounted by the parent
    const exitTimeout = setTimeout(() => setVisible(false), 4500); 
    
    return () => {
        clearTimeout(enterTimeout);
        clearTimeout(exitTimeout);
    };
  }, [trade]);

  if (!trade || trade.stage !== 'trade_executed') {
    return null;
  }

  const { side, pair, size, price } = trade;
  const isLong = String(side).toUpperCase() === 'LONG';
  const sideColor = isLong ? 'border-green-500' : 'border-red-500';
  const sideTextColor = isLong ? 'text-green-400' : 'text-red-400';

  return (
    <div
      className={`fixed top-6 right-6 w-80 bg-gray-800 border-l-4 ${sideColor} rounded-r-lg shadow-2xl p-4 z-50 transition-all duration-500 transform ${visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0'}`}
      role="alert"
      aria-live="assertive"
    >
      <div className="flex items-start">
        <div className="flex-shrink-0 pt-0.5">
          {isLong ? (
             <svg className="h-6 w-6 text-green-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
            </svg>
          ) : (
            <svg className="h-6 w-6 text-red-400" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 17h8m0 0V9m0 8l-8-8-4 4-6-6" />
            </svg>
          )}
        </div>
        <div className="ml-3 w-0 flex-1">
          <p className="text-sm font-bold text-gray-100">Trade Executed</p>
          <div className="mt-2 text-sm text-gray-300 font-mono">
            <p>
              <span className={`font-bold ${sideTextColor}`}>{side}</span> {pair}
            </p>
            <p>Size: {size}</p>
            <p>Price: ${String(price)}</p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TradeNotification;
