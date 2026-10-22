import React, { useState } from 'react';

interface TradeControlsProps {
  onExecuteTrade: (tradeDetails: { pair: string; side: 'LONG' | 'SHORT'; size: string; price: string }) => Promise<void> | void;
  isApiActive: boolean;
}

const TradeControls: React.FC<TradeControlsProps> = ({ onExecuteTrade, isApiActive }) => {
  const [pair, setPair] = useState('ETH/USD');
  const [side, setSide] = useState<'LONG' | 'SHORT'>('LONG');
  const [size, setSize] = useState('1.5');
  const [price, setPrice] = useState('3500.00');

  const handleExecute = async () => {
    if (!pair || !size || !price) {
      alert('Please fill in all trade details.');
      return;
    }

    try {
      await onExecuteTrade({ pair, side, size, price });
    } catch (error) {
      console.error('Trade execution failed:', error);
      alert('Trade execution failed. Check console for details.');
    }
  };

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 h-full flex flex-col">
      <div className="flex-grow">
          <h3 className="text-xl font-semibold text-gray-200 mb-1">Layer 5: Manual Trade Execution</h3>
          <p className="text-sm text-gray-400 mb-6">Execute manual orders. Requires active API key.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor="pair" className="block text-sm font-medium text-gray-400 mb-1">Pair</label>
              <input
                type="text"
                id="pair"
                value={pair}
                onChange={(e) => setPair(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label htmlFor="side" className="block text-sm font-medium text-gray-400 mb-1">Side</label>
              <select
                id="side"
                value={side}
                onChange={(e) => setSide(e.target.value as 'LONG' | 'SHORT')}
                className="w-full bg-gray-900 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500"
              >
                <option value="LONG">LONG</option>
                <option value="SHORT">SHORT</option>
              </select>
            </div>
            <div>
              <label htmlFor="size" className="block text-sm font-medium text-gray-400 mb-1">Size</label>
              <input
                type="number"
                id="size"
                step="0.01"
                value={size}
                onChange={(e) => setSize(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
            <div>
              <label htmlFor="price" className="block text-sm font-medium text-gray-400 mb-1">Price</label>
              <input
                type="number"
                id="price"
                step="0.01"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                className="w-full bg-gray-900 border border-gray-600 rounded-md py-2 px-3 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
            </div>
          </div>
      </div>

      <button
        onClick={handleExecute}
        disabled={!isApiActive}
        className="mt-6 w-full font-bold py-3 px-8 rounded-lg shadow-lg transition-transform transform hover:scale-105 bg-gradient-to-r from-sky-500 to-indigo-600 hover:from-sky-600 hover:to-indigo-700 disabled:bg-gray-600 disabled:from-gray-600 disabled:to-gray-700 disabled:cursor-not-allowed disabled:transform-none disabled:scale-100"
      >
        {isApiActive ? 'EXECUTE TRADE' : 'API INACTIVE'}
      </button>
    </div>
  );
};

export default TradeControls;

