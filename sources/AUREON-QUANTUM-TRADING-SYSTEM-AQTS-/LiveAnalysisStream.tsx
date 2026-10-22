
import React, { useEffect, useRef } from 'react';

interface LiveAnalysisStreamProps {
  commentary: string;
}

const LiveAnalysisStream: React.FC<LiveAnalysisStreamProps> = ({ commentary }) => {
  const contentRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (contentRef.current) {
      contentRef.current.scrollTop = contentRef.current.scrollHeight;
    }
  }, [commentary]);

  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-6 flex flex-col h-[300px] lg:h-auto">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-xl font-semibold text-gray-200">AUREON Live Commentary</h3>
        <div className="flex items-center space-x-2">
            <span className="relative flex h-3 w-3">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-red-400 opacity-75"></span>
                <span className="relative inline-flex rounded-full h-3 w-3 bg-red-500"></span>
            </span>
            <span className="text-sm font-medium text-red-400">LIVE</span>
        </div>
      </div>
      <div 
        ref={contentRef}
        className="flex-grow overflow-y-auto pr-2 text-gray-300 text-sm leading-relaxed font-mono"
      >
        <p style={{ whiteSpace: 'pre-wrap' }}>{commentary || 'Awaiting real-time analysis...'}</p>
      </div>
    </div>
  );
};

export default LiveAnalysisStream;
