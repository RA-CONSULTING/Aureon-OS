import React, { useState, useEffect } from 'react';

interface StormData {
  id: string;
  name: string;
  severity: number;
  type: 'Terrestrial' | 'Celestial';
}

const StormTargetingInterface: React.FC = () => {
  const [stormData, setStormData] = useState<StormData[]>([]);
  const [harmonizationResult, setHarmonizationResult] = useState<any>(null);

  useEffect(() => {
    const eventSource = new EventSource('/stream');
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      // For now, we'll just display the raw data.
      // In the future, we will process this to identify storm threats.
      setStormData(data.storms);
    };
    return () => {
      eventSource.close();
    };
  }, []);

  const handleHarmonize = async () => {
    try {
      const response = await fetch('/harmonize');
      const result = await response.json();
      setHarmonizationResult(result);
    } catch (error) {
      console.error('Error during harmonization:', error);
      setHarmonizationResult({ error: 'Failed to harmonize' });
    }
  };

  return (
    <div>
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold">Storm Targeting Interface</h2>
        <button 
          onClick={handleHarmonize}
          className="bg-teal-500 hover:bg-teal-600 text-white font-bold py-2 px-4 rounded"
        >
          Harmonize
        </button>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h3 className="text-lg font-semibold mb-2">Live Storm Data</h3>
          <div className="space-y-2">
            {stormData.map((storm) => (
              <div key={storm.id} className="bg-stone-800 p-3 rounded-lg">
                <div className="flex justify-between items-center">
                  <span className="font-semibold">{storm.name}</span>
                  <span className={`text-sm ${storm.severity > 7 ? 'text-red-500' : storm.severity > 4 ? 'text-yellow-500' : 'text-green-500'}`}>
                    Severity: {storm.severity}
                  </span>
                </div>
                <div className="text-xs text-stone-400">Type: {storm.type}</div>
              </div>
            ))}
          </div>
        </div>
        <div>
          <h3 className="text-lg font-semibold mb-2">Harmonization Result</h3>
          {harmonizationResult && (
            <pre className="bg-stone-800 p-3 rounded-lg text-xs">
              {JSON.stringify(harmonizationResult, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default StormTargetingInterface;
