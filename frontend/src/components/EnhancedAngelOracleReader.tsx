import { useEffect, useMemo, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Sparkles, Heart, Shuffle, X } from "lucide-react";

const DECK_URL = "/angel-oracle-cards-complete.json";

export type Category = "yes_no" | "timing" | "angel_message";

export interface OracleCard {
  name: string;
  category: Category;
  border_color: "blue" | "gold" | "purple";
  yes_no_value?: string;
  time_window?: string;
  oracle_summary: string;
  nexus_mapping: any;
  tags: string[];
}

const categoryImages = {
  yes_no: "https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756767541393_165922e4.webp",
  timing: "https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756767542233_a1b47cde.webp",
  angel_message: "https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756767542995_14edc185.webp"
};

const EnhancedAngelOracleReader = () => {
  const [oracleData, setOracleData] = useState<any>(null);
  const [drawnCards, setDrawnCards] = useState<OracleCard[]>([]);
  const [question, setQuestion] = useState("");
  const [drawCount, setDrawCount] = useState(3);
  const [isShuffling, setIsShuffling] = useState(false);
  const [selectedCard, setSelectedCard] = useState<OracleCard | null>(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    fetch(DECK_URL, { cache: 'no-store' })
      .then(res => res.ok ? res.json() : Promise.reject())
      .then(setOracleData)
      .catch(console.error);

    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setShowModal(false);
    };
    window.addEventListener('keydown', handleEsc);
    return () => window.removeEventListener('keydown', handleEsc);
  }, []);

  const drawCards = async () => {
    if (!oracleData || !question.trim()) return;
    
    setIsShuffling(true);
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const shuffled = [...oracleData.cards].sort(() => Math.random() - 0.5);
    const drawn = shuffled.slice(0, Math.min(drawCount, 10));
    
    setDrawnCards(drawn);
    setIsShuffling(false);
  };

  const generateReading = (card: OracleCard, question: string) => {
    const readings = {
      yes: `Regarding "${question}" - The angels give you a clear YES.`,
      strong_yes: `For "${question}" - This is a resounding YES!`,
      no: `About "${question}" - The answer is NO, or not at this time.`,
      strong_no: `Concerning "${question}" - This is a firm NO.`,
      probably_no: `For "${question}" - This outcome is unlikely.`,
      continue: `Regarding "${question}" - Don't give up! Keep moving forward.`,
      pivot: `About "${question}" - It's time to choose a new direction.`,
      rethink: `For "${question}" - Take time to reconsider your approach.`,
      better_path: `Concerning "${question}" - There's something better in store.`
    };
    
    return readings[card.yes_no_value as keyof typeof readings] || 
           `The angels offer guidance for "${question}": ${card.oracle_summary}`;
  };

  return (
    <div className="space-y-6">
      <div className="text-center">
        <h2 className="text-2xl font-bold text-white flex items-center justify-center gap-2">
          <Sparkles className="w-6 h-6 text-warning" />
          Enhanced Angel Oracle
          <Heart className="w-6 h-6 text-primary" />
        </h2>
      </div>

      <Card className="bg-slate-700/50 border-slate-600">
        <CardContent className="p-4 space-y-4">
          <Input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask your question..."
            className="bg-slate-800 border-slate-600 text-white"
          />
          <div className="flex gap-4 items-center">
            <label className="text-white">Cards to draw:</label>
            <Input
              type="number"
              min="1"
              max="10"
              value={drawCount}
              onChange={(e) => setDrawCount(Number(e.target.value))}
              className="w-20 bg-slate-800 border-slate-600 text-white"
            />
            <Button
              onClick={drawCards}
              disabled={isShuffling || !question.trim()}
              className="bg-gradient-to-r from-primary to-primary"
            >
              {isShuffling ? <Shuffle className="w-4 h-4 animate-spin" /> : 'Draw Cards'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {drawnCards.length > 0 && (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {drawnCards.map((card, index) => (
            <div key={index} className="relative group">
              <div className="relative w-full aspect-[3/4] mb-4 cursor-pointer transform transition-all duration-300 hover:scale-105"
                   onClick={() => { setSelectedCard(card); setShowModal(true); }}>
                <div className="absolute inset-0 rounded-lg overflow-hidden shadow-2xl">
                  <img 
                    src={categoryImages[card.category]}
                    alt={`${card.category} Angel Oracle Card`}
                    className="w-full h-full object-cover"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent" />
                  <div className="absolute bottom-4 left-4 right-4 text-center">
                    <h3 className="text-white font-bold text-lg mb-1">{card.name}</h3>
                    <Badge className={`${card.border_color === 'blue' ? 'bg-primary' : 
                                      card.border_color === 'gold' ? 'bg-warning' : 'bg-primary'}`}>
                      {card.category.replace('_', ' ')}
                    </Badge>
                  </div>
                </div>
              </div>
              
              <Card className="bg-slate-700/50 border-slate-600">
                <CardContent className="p-4">
                  <p className="text-gray-300 text-sm leading-relaxed">{generateReading(card, question)}</p>
                </CardContent>
              </Card>
            </div>
          ))}
        </div>
      )}

      {showModal && selectedCard && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50" role="dialog" aria-modal="true">
          <Card className="max-w-md w-full m-4 bg-slate-800">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle className="text-white">{selectedCard.name}</CardTitle>
              <Button variant="ghost" size="sm" onClick={() => setShowModal(false)}>
                <X className="w-4 h-4" />
              </Button>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-gray-300">{selectedCard.oracle_summary}</p>
              <div className="flex flex-wrap gap-2">
                {selectedCard.tags.map((tag, i) => (
                  <Badge key={i} variant="secondary">{tag}</Badge>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default EnhancedAngelOracleReader;