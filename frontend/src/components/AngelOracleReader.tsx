import React, { useState, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import { Button } from './ui/button';
import { Badge } from './ui/badge';
import { Shuffle, Sparkles, Heart } from 'lucide-react';

interface OracleCard {
  name: string;
  category: string;
  border_color: string;
  yes_no_value?: string;
  time_window?: string;
  oracle_summary: string;
  nexus_mapping: {
    op_type?: string;
    signal?: string;
    effect?: string;
    time_gate?: string;
    probability?: number;
    action?: string;
  };
  tags: string[];
}

interface AngelOracleData {
  deck: {
    name: string;
    authors: string[];
    total_cards: number;
    categories: Record<string, any>;
  };
  cards: OracleCard[];
}

const AngelOracleReader: React.FC = () => {
  const [oracleData, setOracleData] = useState<AngelOracleData | null>(null);
  const [selectedCard, setSelectedCard] = useState<OracleCard | null>(null);
  const [isShuffling, setIsShuffling] = useState(false);
  const [question, setQuestion] = useState('');

  const cardImages = [
    'https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756765189840_0ddf4f37.webp',
    'https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756765195797_f583592d.webp',
    'https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756765199380_37d0f30a.webp'
  ];

  const cardBackImage = 'https://d64gsuwffb70l.cloudfront.net/68b55da3cc8df3f651647221_1756765184037_5659355b.webp';

  useEffect(() => {
    const loadOracleData = async () => {
      try {
        const response = await fetch('/angel-oracle-cards.json');
        const data = await response.json();
        setOracleData(data);
      } catch (error) {
        console.error('Failed to load oracle data:', error);
      }
    };
    loadOracleData();
  }, []);

  const drawCard = async () => {
    if (!oracleData) return;
    
    setIsShuffling(true);
    setSelectedCard(null);
    
    // Simulate shuffling animation
    await new Promise(resolve => setTimeout(resolve, 1500));
    
    const allCards = oracleData.cards;
    const randomCard = allCards[Math.floor(Math.random() * allCards.length)];
    
    setSelectedCard(randomCard);
    setIsShuffling(false);
  };

  const getBorderColor = (color: string) => {
    switch (color) {
      case 'blue': return 'border-primary';
      case 'gold': return 'border-warning';
      case 'purple': return 'border-primary';
      default: return 'border-gray-400';
    }
  };

  const getCategoryIcon = (category: string) => {
    switch (category) {
      case 'yes_no': return '💙';
      case 'timing': return '⏰';
      case 'angel_messages': return '💜';
      default: return '✨';
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-4">
        <div className="flex items-center justify-center gap-2 mb-4">
          <Sparkles className="w-6 h-6 text-warning" />
          <h2 className="text-2xl font-bold text-white">Angel Answers Oracle</h2>
          <Heart className="w-6 h-6 text-primary" />
        </div>
        
        <p className="text-gray-300 max-w-2xl mx-auto">
          Ask a question and receive divine guidance from the angels. Focus on your question and draw a card for clear answers.
        </p>
      </div>

      <Card className="bg-slate-700/50 border-slate-600">
        <CardHeader>
          <CardTitle className="text-white flex items-center gap-2">
            🙏 Ask Your Question
          </CardTitle>
        </CardHeader>
        <CardContent>
          <textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="What would you like guidance on today?"
            className="w-full p-3 bg-slate-800 border border-slate-600 rounded-lg text-white placeholder-gray-400 resize-none"
            rows={3}
          />
        </CardContent>
      </Card>

      <div className="text-center">
        <Button
          onClick={drawCard}
          disabled={isShuffling || !question.trim()}
          className="bg-gradient-to-r from-primary to-primary hover:from-primary hover:to-primary text-white px-8 py-3 text-lg"
        >
          {isShuffling ? (
            <>
              <Shuffle className="w-5 h-5 mr-2 animate-spin" />
              Connecting with Angels...
            </>
          ) : (
            <>
              <Sparkles className="w-5 h-5 mr-2" />
              Draw Angel Card
            </>
          )}
        </Button>
      </div>

      {isShuffling && (
        <div className="flex justify-center">
          <div className="relative">
            <img
              src={cardBackImage}
              alt="Card back"
              className="w-32 h-44 rounded-lg shadow-lg animate-pulse"
            />
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-pulse rounded-lg"></div>
          </div>
        </div>
      )}

      {selectedCard && !isShuffling && (
        <Card className={`bg-slate-700/50 border-2 ${getBorderColor(selectedCard.border_color)} shadow-xl`}>
          <CardHeader className="text-center">
            <div className="flex justify-center mb-4">
              <img
                src={cardImages[Math.floor(Math.random() * cardImages.length)]}
                alt={selectedCard.name}
                className="w-40 h-56 rounded-lg shadow-lg"
              />
            </div>
            <CardTitle className="text-2xl text-white flex items-center justify-center gap-2">
              {getCategoryIcon(selectedCard.category)} {selectedCard.name}
            </CardTitle>
            <Badge variant="outline" className={`${getBorderColor(selectedCard.border_color)} text-white`}>
              {selectedCard.category.replace('_', ' ').toUpperCase()}
            </Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="bg-slate-800/50 p-4 rounded-lg">
              <h4 className="text-warning font-semibold mb-2">✨ Oracle Summary</h4>
              <p className="text-gray-300">{selectedCard.oracle_summary}</p>
            </div>
            {selectedCard.yes_no_value && (
              <div className="bg-slate-800/50 p-4 rounded-lg">
                <h4 className="text-primary font-semibold mb-2">🔮 Answer</h4>
                <p className="text-gray-300 font-semibold text-lg">{selectedCard.yes_no_value.replace('_', ' ').toUpperCase()}</p>
              </div>
            )}
            {selectedCard.time_window && (
              <div className="bg-slate-800/50 p-4 rounded-lg">
                <h4 className="text-success font-semibold mb-2">⏰ Timing</h4>
                <p className="text-gray-300">{selectedCard.time_window}</p>
              </div>
            )}
            <div className="bg-slate-800/50 p-4 rounded-lg">
              <h4 className="text-primary font-semibold mb-2">🏷️ Tags</h4>
              <div className="flex flex-wrap gap-2">
                {selectedCard.tags.map((tag, index) => (
                  <Badge key={index} variant="secondary" className="text-xs">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {oracleData && (
        <Card className="bg-slate-700/50 border-slate-600">
          <CardHeader>
            <CardTitle className="text-white">📚 About This Deck</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
              <div className="text-center">
                <div className="text-primary text-2xl mb-2">💙</div>
                <h4 className="text-white font-semibold">Yes/No Cards</h4>
                <p className="text-gray-400">Clear answers to direct questions</p>
              </div>
              <div className="text-center">
                <div className="text-warning text-2xl mb-2">⏰</div>
                <h4 className="text-white font-semibold">Timing Cards</h4>
                <p className="text-gray-400">When things will happen</p>
              </div>
              <div className="text-center">
                <div className="text-primary text-2xl mb-2">💜</div>
                <h4 className="text-white font-semibold">Angel Messages</h4>
                <p className="text-gray-400">Divine guidance and wisdom</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AngelOracleReader;