import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { TarotEngine, TarotReading } from '@/lib/tarot-engine';

interface TarotReaderProps {
  name?: string;
  dob?: string;
  tob?: string;
  pob?: string;
}

export function TarotReader({ name = "Seeker", dob = "1990-01-01" }: TarotReaderProps) {
  const [reading, setReading] = useState<TarotReading | null>(null);
  const [loading, setLoading] = useState(false);
  const [voice, setVoice] = useState<'mythic' | 'plain'>('mythic');
  const [engine] = useState(() => new TarotEngine());

  const generateReading = async () => {
    setLoading(true);
    try {
      const newReading = await engine.generateReading(name, dob);
      setReading(newReading);
    } catch (error) {
      console.error('Failed to generate tarot reading:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    generateReading();
  }, [name, dob]);

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary mx-auto mb-4"></div>
          <p className="text-muted-foreground">Drawing cards...</p>
        </div>
      </div>
    );
  }

  if (!reading) {
    return (
      <div className="text-center p-8">
        <p className="text-muted-foreground mb-4">Unable to generate reading</p>
        <Button onClick={generateReading}>Try Again</Button>
      </div>
    );
  }

  const CardDisplay = ({ position, data }: { position: string; data: any }) => (
    <Card className="mb-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-lg">{data.card.name}</CardTitle>
          <Badge variant={data.orientation === 'upright' ? 'default' : 'secondary'}>
            {data.orientation}
          </Badge>
        </div>
        <CardDescription className="capitalize font-medium">{position}</CardDescription>
      </CardHeader>
      <CardContent>
        <p className="text-sm text-muted-foreground mb-2">
          {data.orientation === 'upright' ? data.card.upright : data.card.reversed}
        </p>
        <p className="text-sm font-medium mb-1">Lesson: {data.card.lesson}</p>
        <p className="text-sm text-warning">Warning: {data.card.warning}</p>
        <div className="flex flex-wrap gap-1 mt-2">
          {data.card.keywords.map((keyword: string) => (
            <Badge key={keyword} variant="outline" className="text-xs">
              {keyword}
            </Badge>
          ))}
        </div>
      </CardContent>
    </Card>
  );

  return (
    <div className="space-y-6">
      {/* Voice Toggle */}
      <div className="flex justify-center">
        <Tabs value={voice} onValueChange={(v) => setVoice(v as 'mythic' | 'plain')}>
          <TabsList>
            <TabsTrigger value="mythic">Mythic Voice</TabsTrigger>
            <TabsTrigger value="plain">Plain Voice</TabsTrigger>
          </TabsList>
        </Tabs>
      </div>

      {/* Narrative */}
      <Card>
        <CardHeader>
          <CardTitle>Your Tarot Reading</CardTitle>
          <CardDescription>QAID: {reading.qaid.substring(0, 8)}...</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm leading-relaxed">
            {voice === 'mythic' ? reading.narrative.mythic : reading.narrative.plain}
          </p>
        </CardContent>
      </Card>

      {/* Four Pillars Layout */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <CardDisplay position="origins" data={reading.positions.origins} />
        <CardDisplay position="present" data={reading.positions.present} />
      </div>

      {/* Future Paths */}
      <Card>
        <CardHeader>
          <CardTitle>Future Paths</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <CardDisplay position="aligned path" data={reading.positions.aligned} />
            <CardDisplay position="middle path" data={reading.positions.middle} />
            <CardDisplay position="resistant path" data={reading.positions.resistant} />
          </div>
        </CardContent>
      </Card>

      {/* Unity */}
      <CardDisplay position="unity & integration" data={reading.positions.unity} />

      {/* Practices */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Practices</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {Object.entries(reading.practices).map(([practice, weight]) => (
              <div key={practice} className="text-center">
                <div className="text-2xl font-bold text-primary">
                  {Math.round(weight * 100)}%
                </div>
                <div className="text-sm text-muted-foreground capitalize">
                  {practice}
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <Button onClick={generateReading} className="w-full">
        Draw New Reading
      </Button>
    </div>
  );
}