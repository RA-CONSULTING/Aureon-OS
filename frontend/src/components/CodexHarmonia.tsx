import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const CodexHarmonia = () => {
  const [activeSymbol, setActiveSymbol] = useState('circle');
  const [meditationActive, setMeditationActive] = useState(false);

  const sacredSymbols = {
    circle: { symbol: '○', meaning: 'Unity & Wholeness', energy: 'Infinite' },
    triangle: { symbol: '△', meaning: 'Ascension & Balance', energy: 'Directed' },
    square: { symbol: '□', meaning: 'Foundation & Stability', energy: 'Grounded' },
    star: { symbol: '✦', meaning: 'Divine Connection', energy: 'Radiant' },
    infinity: { symbol: '∞', meaning: 'Eternal Flow', energy: 'Continuous' }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-primary to-primary p-6">
      <div className="max-w-6xl mx-auto space-y-6">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-white mb-4">
            CODEX HARMONIA
          </h1>
          <p className="text-xl text-primary">
            Sacred Geometry & Consciousness Integration
          </p>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <Card className="bg-black/50 border-primary">
            <CardHeader>
              <CardTitle className="text-primary">Sacred Symbol Matrix</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-4 mb-6">
                {Object.entries(sacredSymbols).map(([key, data]) => (
                  <Button
                    key={key}
                    variant={activeSymbol === key ? "default" : "outline"}
                    onClick={() => setActiveSymbol(key)}
                    className="h-16 text-2xl"
                  >
                    {data.symbol}
                  </Button>
                ))}
              </div>
              
              <div className="bg-primary/30 p-4 rounded-lg">
                <h4 className="text-primary font-semibold mb-2">
                  {sacredSymbols[activeSymbol as keyof typeof sacredSymbols].meaning}
                </h4>
                <p className="text-primary text-sm">
                  Energy Type: {sacredSymbols[activeSymbol as keyof typeof sacredSymbols].energy}
                </p>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-black/50 border-primary">
            <CardHeader>
              <CardTitle className="text-primary">Hermetic Wisdom</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="text-center mb-6">
                  <div className="w-24 h-24 mx-auto mb-4 relative">
                    <div className="w-full h-full rounded-full border-4 border-warning flex items-center justify-center bg-gradient-to-br from-warning to-warning">
                      <div className="text-2xl">🗝️</div>
                    </div>
                  </div>
                  <p className="text-warning font-semibold">The Key of Understanding</p>
                </div>
                
                <div className="space-y-3 text-sm">
                  <div className="bg-warning/30 p-3 rounded-lg">
                    <p className="text-warning">
                      "As above, so below; as within, so without"
                    </p>
                  </div>
                  
                  <div className="bg-primary/30 p-3 rounded-lg">
                    <p className="text-primary">
                      Sacred geometry reveals the blueprint of consciousness
                    </p>
                  </div>
                  
                  <div className="bg-primary/30 p-3 rounded-lg">
                    <p className="text-primary">
                      The Flower of Life contains all creation patterns
                    </p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        <Card className="bg-black/50 border-primary">
          <CardHeader>
            <CardTitle className="text-primary">Meditation Gateway</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-center space-y-6">
              <div className="relative">
                <div className={`w-48 h-48 mx-auto rounded-full border-4 ${meditationActive ? 'border-primary animate-pulse' : 'border-primary'} flex items-center justify-center bg-gradient-to-br from-primary to-primary`}>
                  <div className="text-6xl">🧘</div>
                </div>
                
                {meditationActive && (
                  <>
                    <div className="absolute inset-0 rounded-full border-4 border-primary animate-ping"></div>
                    <div className="absolute inset-4 rounded-full border-2 border-primary animate-pulse"></div>
                  </>
                )}
              </div>
              
              <Button 
                onClick={() => setMeditationActive(!meditationActive)}
                className={`px-8 py-3 text-lg ${meditationActive ? 'bg-success hover:bg-success' : 'bg-primary hover:bg-primary'}`}
              >
                {meditationActive ? 'IN MEDITATION' : 'ENTER MEDITATION'}
              </Button>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
                <div className="bg-primary/30 p-4 rounded-lg">
                  <Badge className="mb-2">TAKE ME HOME</Badge>
                  <p className="text-sm text-primary">Return to source frequency</p>
                </div>
                
                <div className="bg-primary/30 p-4 rounded-lg">
                  <Badge className="mb-2">SACRED UNION</Badge>
                  <p className="text-sm text-primary">Divine masculine & feminine balance</p>
                </div>
                
                <div className="bg-primary/30 p-4 rounded-lg">
                  <Badge className="mb-2">HARMONIC ALIGNMENT</Badge>
                  <p className="text-sm text-primary">Frequency synchronization</p>
                </div>
              </div>
              
              {meditationActive && (
                <div className="bg-gradient-to-r from-primary/50 to-primary/50 p-4 rounded-lg mt-6">
                  <p className="text-white italic">
                    "In the silence between thoughts, the infinite speaks..."
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default CodexHarmonia;