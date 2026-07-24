import React, { useEffect, useState } from 'react';
import { useHarmonicAuth } from '@/hooks/useHarmonicAuth';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Badge } from './ui/badge';
import { Button } from './ui/button';

interface LiveDataStream {
  timestamp: number;
  source: 'schumann' | 'aura' | 'validation';
  data: any;
}

export function LiveDataPuller() {
  const { session, isAuthenticated, getAuthHeaders } = useHarmonicAuth();
  const [streams, setStreams] = useState<LiveDataStream[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [wsConnection, setWsConnection] = useState<WebSocket | null>(null);

  useEffect(() => {
    if (!isAuthenticated || !session) return;

    const connectToLiveData = () => {
      try {
        const ws = new WebSocket('ws://localhost:8787');
        
        ws.onopen = () => {
          console.log('🔗 Connected to live data stream');
          setIsConnected(true);
          
          // Send authentication
          ws.send(JSON.stringify({
            type: 'auth',
            session_token: session.session_token,
            charter_id: session.charter_id
          }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            
            const newStream: LiveDataStream = {
              timestamp: Date.now(),
              source: data.source || 'validation',
              data: data
            };

            setStreams(prev => [...prev.slice(-49), newStream]);
          } catch (error) {
            console.error('Failed to parse live data:', error);
          }
        };

        ws.onclose = () => {
          console.log('🔌 Live data stream disconnected');
          setIsConnected(false);
          
          // Reconnect after 3 seconds
          setTimeout(connectToLiveData, 3000);
        };

        ws.onerror = (error) => {
          console.error('WebSocket error:', error);
          setIsConnected(false);
        };

        setWsConnection(ws);
      } catch (error) {
        console.error('Failed to connect to live data:', error);
        setIsConnected(false);
      }
    };

    connectToLiveData();

    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
    };
  }, [isAuthenticated, session]);

  const clearStreams = () => {
    setStreams([]);
  };

  if (!isAuthenticated) {
    return (
      <Card className="bg-black/40 border-destructive/30">
        <CardHeader>
          <CardTitle className="text-destructive">Live Data Access Denied</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-destructive">Authentication required for live data streams</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="bg-black/40 border-primary/30">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-primary flex items-center gap-2">
            📡 Live Data Streams
            <Badge variant={isConnected ? "default" : "destructive"}>
              {isConnected ? 'Connected' : 'Disconnected'}
            </Badge>
          </CardTitle>
          <Button 
            onClick={clearStreams}
            variant="outline"
            size="sm"
            className="border-primary text-primary"
          >
            Clear
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {streams.length === 0 ? (
            <div className="text-center py-8 text-primary">
              Waiting for live data streams...
            </div>
          ) : (
            streams.map((stream, index) => (
              <div key={index} className="bg-black/20 rounded p-3 text-sm">
                <div className="flex items-center justify-between mb-2">
                  <Badge 
                    variant="outline" 
                    className={`
                      ${stream.source === 'schumann' ? 'border-primary text-primary' : ''}
                      ${stream.source === 'aura' ? 'border-success text-success' : ''}
                      ${stream.source === 'validation' ? 'border-primary text-primary' : ''}
                    `}
                  >
                    {stream.source}
                  </Badge>
                  <span className="text-gray-400">
                    {new Date(stream.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                <pre className="text-xs text-gray-300 overflow-x-auto">
                  {JSON.stringify(stream.data, null, 2)}
                </pre>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}