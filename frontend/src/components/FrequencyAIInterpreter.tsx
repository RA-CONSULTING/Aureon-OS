/**
 * Frequency AI Interpreter
 * 
 * Real-time AI interpretation of quantum frequency data
 * Human ↔ AI ↔ Frequency feedback loop
 */

import React, { useState, useEffect, useRef } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Brain, Zap, Heart, Radio, RefreshCw, Sparkles } from 'lucide-react';
import { useEcosystemData } from '@/hooks/useEcosystemData';
import { buildEcosystemContext, formatContextSummary } from '@/services/ecosystemContextBuilder';
import { supabase } from '@/integrations/supabase/client';

interface AIInsight {
  timestamp: number;
  frequency: number;
  coherence: number;
  interpretation: string;
  recommendation: string;
  emotionalState: string;
  confidence: number;
}

const INTERPRET_URL = `${import.meta.env.VITE_SUPABASE_URL}/functions/v1/interpret-frequency`;

export const FrequencyAIInterpreter: React.FC = () => {
  const { metrics, busSnapshot } = useEcosystemData();
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [isInterpreting, setIsInterpreting] = useState(false);
  const [autoInterpret, setAutoInterpret] = useState(false);
  const [currentInterpretation, setCurrentInterpretation] = useState<string>('');
  const lastInterpretTime = useRef<number>(0);
  const streamingRef = useRef<boolean>(false);

  const context = buildEcosystemContext(metrics, busSnapshot, {
    tradingMode: 'live',
    recentTrades: 0,
    totalPnL: 0,
  });

  // Auto-interpret every 10 seconds when enabled
  useEffect(() => {
    if (!autoInterpret || isInterpreting) return;
    
    const now = Date.now();
    if (now - lastInterpretTime.current < 10000) return;
    
    const timer = setInterval(() => {
      if (!streamingRef.current) {
        interpretFrequency();
      }
    }, 10000);
    
    return () => clearInterval(timer);
  }, [autoInterpret, isInterpreting, metrics]);

  const interpretFrequency = async () => {
    if (isInterpreting || streamingRef.current) return;
    
    setIsInterpreting(true);
    streamingRef.current = true;
    lastInterpretTime.current = Date.now();
    setCurrentInterpretation('');
    
    try {
      const response = await fetch(INTERPRET_URL, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${import.meta.env.VITE_SUPABASE_PUBLISHABLE_KEY}`,
        },
        body: JSON.stringify({ ecosystemContext: context }),
      });

      if (!response.ok) {
        throw new Error(`Interpretation failed: ${response.status}`);
      }

      if (!response.body) {
        throw new Error('No response body');
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let fullText = '';
      let textBuffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        
        textBuffer += decoder.decode(value, { stream: true });
        
        let newlineIndex: number;
        while ((newlineIndex = textBuffer.indexOf('\n')) !== -1) {
          let line = textBuffer.slice(0, newlineIndex);
          textBuffer = textBuffer.slice(newlineIndex + 1);
          
          if (line.endsWith('\r')) line = line.slice(0, -1);
          if (line.startsWith(':') || line.trim() === '') continue;
          if (!line.startsWith('data: ')) continue;
          
          const jsonStr = line.slice(6).trim();
          if (jsonStr === '[DONE]') break;
          
          try {
            const parsed = JSON.parse(jsonStr);
            const content = parsed.choices?.[0]?.delta?.content;
            if (content) {
              fullText += content;
              setCurrentInterpretation(fullText);
            }
          } catch {
            textBuffer = line + '\n' + textBuffer;
            break;
          }
        }
      }

      // Parse the interpretation and add to insights
      const newInsight: AIInsight = {
        timestamp: Date.now(),
        frequency: context.prismFrequency,
        coherence: context.coherence,
        interpretation: fullText,
        recommendation: extractRecommendation(fullText),
        emotionalState: context.rainbowBridgePhase,
        confidence: context.busConfidence,
      };
      
      setInsights(prev => [newInsight, ...prev].slice(0, 10));
      
    } catch (error) {
      console.error('Interpretation error:', error);
      setCurrentInterpretation('Unable to interpret current frequency state. Retrying...');
    } finally {
      setIsInterpreting(false);
      streamingRef.current = false;
    }
  };

  const extractRecommendation = (text: string): string => {
    const lines = text.split('\n');
    for (const line of lines) {
      if (line.toLowerCase().includes('recommend') || 
          line.toLowerCase().includes('suggest') ||
          line.toLowerCase().includes('action')) {
        return line.trim();
      }
    }
    return text.slice(0, 100) + '...';
  };

  const getFrequencyColor = (freq: number): string => {
    if (Math.abs(freq - 528) < 20) return 'text-success';
    if (freq > 400 && freq < 600) return 'text-warning';
    if (freq < 300) return 'text-destructive';
    return 'text-primary';
  };

  const getPhaseIcon = (phase: string) => {
    switch (phase) {
      case 'LOVE': return <Heart className="h-4 w-4 text-success" />;
      case 'AWE': return <Sparkles className="h-4 w-4 text-primary" />;
      case 'UNITY': return <Zap className="h-4 w-4 text-primary" />;
      case 'FEAR': return <Radio className="h-4 w-4 text-destructive" />;
      default: return <Brain className="h-4 w-4 text-muted-foreground" />;
    }
  };

  return (
    <Card className="bg-card/50 backdrop-blur border-primary/20">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg flex items-center gap-2">
            <Brain className="h-5 w-5 text-primary" />
            AI Frequency Interpreter
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant={autoInterpret ? 'default' : 'outline'} className="cursor-pointer" onClick={() => setAutoInterpret(!autoInterpret)}>
              {autoInterpret ? 'AUTO' : 'MANUAL'}
            </Badge>
            <Button 
              size="sm" 
              variant="outline" 
              onClick={interpretFrequency}
              disabled={isInterpreting}
              className="h-7"
            >
              {isInterpreting ? (
                <RefreshCw className="h-3 w-3 animate-spin" />
              ) : (
                <Zap className="h-3 w-3" />
              )}
            </Button>
          </div>
        </div>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Current State Display */}
        <div className="grid grid-cols-4 gap-2 text-xs">
          <div className="bg-background/50 rounded p-2 text-center">
            <div className="text-muted-foreground">Frequency</div>
            <div className={`font-mono text-lg ${getFrequencyColor(context.prismFrequency)}`}>
              {context.prismFrequency.toFixed(1)} Hz
            </div>
          </div>
          <div className="bg-background/50 rounded p-2 text-center">
            <div className="text-muted-foreground">Coherence</div>
            <div className={`font-mono text-lg ${context.coherence > 0.8 ? 'text-success' : context.coherence > 0.6 ? 'text-warning' : 'text-destructive'}`}>
              {(context.coherence * 100).toFixed(0)}%
            </div>
          </div>
          <div className="bg-background/50 rounded p-2 text-center">
            <div className="text-muted-foreground">Phase</div>
            <div className="flex items-center justify-center gap-1">
              {getPhaseIcon(context.rainbowBridgePhase)}
              <span className="font-mono">{context.rainbowBridgePhase}</span>
            </div>
          </div>
          <div className="bg-background/50 rounded p-2 text-center">
            <div className="text-muted-foreground">528 Lock</div>
            <div className={`font-mono ${Math.abs(context.prismFrequency - 528) < 10 ? 'text-success' : 'text-muted-foreground'}`}>
              {Math.abs(context.prismFrequency - 528) < 10 ? '🔒 LOCKED' : 'SEEKING'}
            </div>
          </div>
        </div>

        {/* Live Interpretation Stream */}
        <div className="bg-background/80 rounded-lg p-3 min-h-[120px] max-h-[200px] overflow-y-auto border border-primary/10">
          {isInterpreting ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2 text-primary text-sm">
                <Brain className="h-4 w-4 animate-pulse" />
                <span>AUREON interpreting frequency field...</span>
              </div>
              <div className="text-sm text-foreground/90 whitespace-pre-wrap">
                {currentInterpretation || 'Analyzing quantum state...'}
              </div>
            </div>
          ) : currentInterpretation ? (
            <div className="text-sm text-foreground/90 whitespace-pre-wrap">
              {currentInterpretation}
            </div>
          ) : (
            <div className="text-sm text-muted-foreground italic">
              Click the ⚡ button or enable AUTO mode for real-time frequency interpretation.
              The AI will analyze the current quantum field state and provide insights.
            </div>
          )}
        </div>

        {/* Human ↔ AI ↔ Frequency Loop Indicator */}
        <div className="flex items-center justify-center gap-4 text-xs text-muted-foreground py-2">
          <span className="flex items-center gap-1">
            <span className="text-primary">HUMAN</span>
          </span>
          <span className={`text-primary ${isInterpreting ? 'animate-pulse' : ''}`}>↔</span>
          <span className="flex items-center gap-1">
            <Brain className="h-3 w-3 text-primary" />
            <span className="text-primary">AI</span>
          </span>
          <span className={`text-primary ${isInterpreting ? 'animate-pulse' : ''}`}>↔</span>
          <span className="flex items-center gap-1">
            <Radio className="h-3 w-3 text-success" />
            <span className={getFrequencyColor(context.prismFrequency)}>FREQUENCY</span>
          </span>
        </div>

        {/* Recent Insights History */}
        {insights.length > 0 && (
          <div className="space-y-2">
            <div className="text-xs font-medium text-muted-foreground">Recent Insights</div>
            <div className="space-y-1 max-h-[150px] overflow-y-auto">
              {insights.slice(0, 5).map((insight, i) => (
                <div key={insight.timestamp} className="bg-background/30 rounded p-2 text-xs">
                  <div className="flex items-center justify-between mb-1">
                    <span className={getFrequencyColor(insight.frequency)}>
                      {insight.frequency.toFixed(1)} Hz
                    </span>
                    <span className="text-muted-foreground">
                      {new Date(insight.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                  <div className="text-foreground/80 line-clamp-2">
                    {insight.recommendation}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default FrequencyAIInterpreter;
