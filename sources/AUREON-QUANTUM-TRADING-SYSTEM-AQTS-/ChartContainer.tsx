
import React from 'react';

interface ChartContainerProps {
  title: string;
  children: React.ReactNode;
}

const ChartContainer: React.FC<ChartContainerProps> = ({ title, children }) => {
  return (
    <div className="bg-gray-800/50 border border-gray-700 rounded-lg shadow-lg p-4 pt-2 pb-4 h-96 flex flex-col">
      <h3 className="text-lg font-semibold text-gray-300 mb-4 text-center">{title}</h3>
      <div className="flex-grow w-full h-full">
        {children}
      </div>
    </div>
  );
};

export default ChartContainer;
