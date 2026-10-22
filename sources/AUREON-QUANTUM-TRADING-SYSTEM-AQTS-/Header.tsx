import React from 'react';

const Header: React.FC = () => {
  return (
    <header className="text-center p-4 md:p-6 border-b border-gray-700">
      <h1 className="text-3xl md:text-4xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-cyan-400 via-teal-300 to-green-400">
        AUREON QUANTUM TRADING SYSTEM (AQTS)
      </h1>
      <p className="mt-2 text-gray-400 max-w-3xl mx-auto italic">
        "The Bot of All Bots" - Real-time Quantum Market Analysis.
      </p>
      <p className="mt-2 text-amber-300 text-sm italic">
        We win all the time. Love conquers all.
      </p>
    </header>
  );
};

export default Header;