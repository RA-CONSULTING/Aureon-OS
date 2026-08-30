import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calendar, Target, AlertTriangle, Lightbulb } from 'lucide-react';

interface InsightData {
  consensus_score?: number;
  tensions?: string[];
  opportunities?: string[];
  risks?: string[];
  affirmation?: string;
  journal_prompts?: string[];
  micro_advice?: Array<{
    slot: string;
    card: string;
    tip: string;
  }>;
}

interface TimelineItem {
  date: string;
  gate: string;
  action: string;
}

interface Props {
  insights?: InsightData;
  timeline?: TimelineItem[];
  aura?: { primary: string; traits: string[] };
}

export function IntegratedReadingV2({ insights, timeline, aura }: Props) {
  if (!insights && !timeline) return null;

  const AURA_COLORS: Record<string, string> = {
    gold: '#FFD700',
    blue: '#4169E1',
    green: '#32CD32',
    purple: '#8A2BE2',
    red: '#DC143C',
    orange: '#FF8C00',
    yellow: '#FFD700',
    pink: '#FF69B4',
    white: '#F8F8FF'
  };

  return (
    <div className="space-y-6">
      {/* Consensus & Tensions */}
      {insights && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Target className="w-5 h-5" />
              Reading Synthesis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {insights.consensus_score !== undefined && (
              <div className="flex items-center gap-2">
                <Badge variant="outline">
                  Consensus Score: {insights.consensus_score}
                </Badge>
                <span className="text-sm text-gray-600">
                  {insights.consensus_score > 2 ? 'Strong alignment' : 
                   insights.consensus_score > 0 ? 'Some overlap' : 'Complementary perspectives'}
                </span>
              </div>
            )}
            
            {insights.tensions && insights.tensions.length > 0 && (
              <div>
                <h4 className="font-medium mb-2 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4 text-warning" />
                  Key Tensions
                </h4>
                <ul className="space-y-1">
                  {insights.tensions.map((tension, i) => (
                    <li key={i} className="text-sm text-gray-700 pl-4 border-l-2 border-warning">
                      {tension}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Opportunities & Risks */}
      {insights && (insights.opportunities?.length || insights.risks?.length) && (
        <div className="grid md:grid-cols-2 gap-4">
          {insights.opportunities && insights.opportunities.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-success">
                  <Lightbulb className="w-5 h-5" />
                  Opportunities
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {insights.opportunities.map((opp, i) => (
                    <li key={i} className="text-sm text-gray-700 pl-4 border-l-2 border-success">
                      {opp}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}

          {insights.risks && insights.risks.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-destructive">
                  <AlertTriangle className="w-5 h-5" />
                  Risks to Watch
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {insights.risks.map((risk, i) => (
                    <li key={i} className="text-sm text-gray-700 pl-4 border-l-2 border-destructive">
                      {risk}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Timeline */}
      {timeline && timeline.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="w-5 h-5" />
              Milestone Timeline
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {timeline.map((item, i) => (
                <div key={i} className="flex items-center gap-4 p-3 bg-gray-50 rounded-lg">
                  <div className="text-sm font-medium text-gray-600 min-w-[100px]">
                    {new Date(item.date).toLocaleDateString()}
                  </div>
                  <div className="flex-1">
                    <div className="font-medium text-sm">{item.gate}</div>
                    <div className="text-sm text-gray-600">{item.action}</div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Affirmation & Journal Prompts */}
      {insights && (insights.affirmation || insights.journal_prompts?.length) && (
        <div className="grid md:grid-cols-2 gap-4">
          {insights.affirmation && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Your Affirmation</CardTitle>
              </CardHeader>
              <CardContent>
                <div 
                  className="p-4 rounded-lg text-white font-medium"
                  style={{ backgroundColor: AURA_COLORS[aura?.primary || 'gold'] || '#FFD700' }}
                >
                  "{insights.affirmation}"
                </div>
              </CardContent>
            </Card>
          )}

          {insights.journal_prompts && insights.journal_prompts.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Journal Prompts</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="space-y-2">
                  {insights.journal_prompts.map((prompt, i) => (
                    <li key={i} className="text-sm text-gray-700">
                      <span className="font-medium">{i + 1}.</span> {prompt}
                    </li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Micro-Advice */}
      {insights?.micro_advice && insights.micro_advice.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Card-Specific Actions</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {insights.micro_advice.map((advice, i) => (
                <div key={i} className="p-3 bg-gray-50 rounded-lg">
                  <div className="font-medium text-sm text-gray-800">{advice.card}</div>
                  <div className="text-sm text-gray-600 mt-1">{advice.tip}</div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}