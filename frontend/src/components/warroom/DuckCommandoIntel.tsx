/**
 *  DUCK COMMANDO INTEL PANEL 
 * =================================
 * 
 * Mission briefing and Duck Commando lore display.
 * Shows active commandos, their assignments, and the Quantum Quackers backstory.
 * 
 * "From the marshlands of Ireland, we rose.
 *  From the hunters of Duck Hunt, we escaped.
 *  Now we hunt pennies. Every single one."
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  DUCK_COMMANDOS_LIST,
  getDuckForExchange,
  getRandomMissionQuote,
} from '../../core/duckCommandos';

interface ExchangeStatus {
  exchange: string;
  connected: boolean;
  // Live sniper telemetry — optional. Omitted until a real kill-tracking source
  // feeds it; the live-stats block only renders when these are present, so the
  // panel never shows fabricated or zero-filled kill numbers.
  activePositions?: number;
  todayKills?: number;
  todayPnl?: number;
}

interface DuckCommandoIntelProps {
  exchangeStatuses?: ExchangeStatus[];
  showLore?: boolean;
}

export function DuckCommandoIntel({ 
  exchangeStatuses = [],
  showLore = true 
}: DuckCommandoIntelProps) {
  const [selectedDuck, setSelectedDuck] = useState<string | null>(null);
  const [showFullLore, setShowFullLore] = useState(false);

  const getStatusForExchange = (exchange: string) => {
    return exchangeStatuses.find(s => s.exchange.toLowerCase() === exchange.toLowerCase());
  };

  return (
    <Card className="bg-gradient-to-br from-slate-900 to-slate-800 border-primary/20 overflow-hidden">
      {/* Commander Banner */}
      <CardHeader className="bg-gradient-to-r from-success/30 via-slate-800 to-warning/30 border-b border-slate-700 pb-3">
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-3">
            <div className="flex flex-col">
              <span className="text-lg font-bold text-foreground">Exchange Scouts</span>
              <span className="text-xs text-muted-foreground">Per-exchange connection intel</span>
            </div>
          </div>
          <Badge className="bg-success/20 text-success border-success/50 text-sm font-bold">
            Live Exchange Intel
          </Badge>
        </div>
      </CardHeader>

      <CardContent className="p-4">
        {/* Mission Statement */}
        <div className="flex items-center justify-center gap-3 mb-4 p-3 bg-muted/40 rounded-lg">
          <span className="text-sm text-muted-foreground italic">Live per-exchange connection status</span>
        </div>

        {/* Irish Tricolor Divider */}
        <div className="flex h-1 mb-4">
          <div className="flex-1 bg-success" />
          <div className="flex-1 bg-white" />
          <div className="flex-1 bg-warning" />
        </div>

        {/* Duck Commandos Section */}
        <h3 className="text-center text-sm font-bold text-foreground mb-3">Exchange Scouts</h3>
        
        <div className="grid grid-cols-2 gap-3 mb-4">
          {DUCK_COMMANDOS_LIST.map((duck) => {
            const status = getStatusForExchange(duck.exchange);
            const isSelected = selectedDuck === duck.codename;
            
            return (
              <div
                key={duck.codename}
                className={`rounded-lg overflow-hidden cursor-pointer transition-all border-2 ${
                  isSelected ? 'border-opacity-100 scale-[1.02]' : 'border-opacity-30 hover:border-opacity-60'
                } bg-slate-800/50`}
                style={{ borderColor: duck.provinceColor }}
                onClick={() => setSelectedDuck(isSelected ? null : duck.codename)}
              >
                {/* Header */}
                <div 
                  className="flex justify-between items-center px-3 py-1.5 text-black text-xs font-semibold"
                  style={{ backgroundColor: duck.provinceColor }}
                >
                  <span>{duck.province} {duck.provinceEmoji}</span>
                  <span className={`w-2 h-2 rounded-full ${status?.connected ? 'bg-success animate-pulse' : 'bg-gray-500'}`} />
                </div>

                {/* Avatar & Identity */}
                <div className="flex flex-col items-center py-3">
                  <span className="text-4xl mb-1">{duck.avatar}</span>
                  <span className="text-sm font-bold text-white">{duck.realName}</span>
                  <span className="text-xs text-warning italic">"{duck.nickname}"</span>
                  <span className="text-[10px] text-gray-500 uppercase tracking-wider">{duck.codename}</span>
                </div>

                {/* Exchange Badge */}
                <div 
                  className="flex items-center justify-center gap-2 mx-2 mb-2 py-1.5 rounded border bg-slate-900/50"
                  style={{ borderColor: duck.provinceColor }}
                >
                  <span className="text-base">{duck.exchangeEmoji}</span>
                  <span className="text-xs font-semibold text-white uppercase">{duck.exchange}</span>
                </div>

                {/* Live sniper telemetry — only when a real kill-tracking source
                    supplies it (never zero-filled/fabricated). */}
                {status && status.todayKills !== undefined && (
                  <div className="grid grid-cols-3 gap-1 px-2 py-2 bg-slate-900/50 border-t border-slate-700">
                    <div className="text-center">
                      <span className="block text-xs"></span>
                      <span className="block text-sm font-bold text-white">{status.todayKills}</span>
                      <span className="block text-[9px] text-gray-500">Kills</span>
                    </div>
                    <div className="text-center">
                      <span className="block text-xs"></span>
                      <span className="block text-sm font-bold text-white">{status.activePositions ?? 0}</span>
                      <span className="block text-[9px] text-gray-500">Active</span>
                    </div>
                    <div className="text-center">
                      <span className="block text-xs"></span>
                      <span className={`block text-sm font-bold ${(status.todayPnl ?? 0) >= 0 ? 'text-success' : 'text-destructive'}`}>
                        ${(status.todayPnl ?? 0).toFixed(2)}
                      </span>
                      <span className="block text-[9px] text-gray-500">PnL</span>
                    </div>
                  </div>
                )}

                {/* Expanded Info */}
                {isSelected && (
                  <div className="p-3 border-t border-slate-700 animate-in fade-in duration-300">
                    <p className="text-xs text-gray-400 mb-2 leading-relaxed">{duck.backstory}</p>
                    <p className="text-xs text-warning italic">
                       "{getRandomMissionQuote(duck.exchange)}"
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Lore Section */}
        {showLore && (
          <div className="border-t border-slate-700">
            <Button 
              variant="ghost"
              className="w-full text-gray-400 hover:text-white text-sm py-3"
              onClick={() => setShowFullLore(!showFullLore)}
            >
              {showFullLore ? ' Hide Origin Story' : ' The Origin Story'}
            </Button>
            
            {showFullLore && (
              <ScrollArea className="h-[200px]">
                <div className="px-4 pb-4 animate-in fade-in duration-300">
                  <h4 className="text-center text-warning font-bold mb-3"> THE QUANTUM QUACKERS REBELLION</h4>
                  <p className="text-xs text-gray-400 leading-relaxed mb-2 text-justify">
                    Long ago, in the misty marshlands of Ireland, there lived an elite breed of ducks. 
                    The British Crown, in their infinite cruelty, created a program called "Duck Hunt" – 
                    not a game, but a systematic hunting of Irish ducks for sport by the English elite.
                  </p>
                  <p className="text-xs text-gray-400 leading-relaxed mb-2 text-justify">
                    From this darkness rose <span className="text-warning font-bold">Quantum Quackers</span>, a duck of extraordinary 
                    intelligence who organized the great escape. He gathered the finest ducks from each 
                    of Ireland's four provinces: Ulster, Munster, Leinster, and Connacht.
                  </p>
                  <p className="text-xs text-gray-400 leading-relaxed mb-2 text-justify">
                    Now, these Duck Commandos have found a new purpose: hunting pennies on the financial 
                    markets. Each commando patrols one exchange – Kraken, Binance, Alpaca, and Capital.com – 
                    extracting micro-profits one trade at a time.
                  </p>
                  <p className="text-sm text-warning italic text-center mt-4">
                    "They hunted us for sport. Now we hunt for profit. Every penny is a victory."
                  </p>
                </div>
              </ScrollArea>
            )}
          </div>
        )}

        {/* Footer Quote */}
        <div className="flex items-center justify-center gap-3 pt-3 mt-4 border-t border-slate-700">
          <span className="text-base"></span>
          <span className="text-xs text-gray-500 italic">
            "Four ducks. Four provinces. Four exchanges. One mission."
          </span>
          <span className="text-base"></span>
        </div>
      </CardContent>
    </Card>
  );
}

export default DuckCommandoIntel;
