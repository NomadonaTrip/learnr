'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Eye, EyeOff, Star } from 'lucide-react';

interface ReviewCardProps {
  card: {
    card_id: string;
    front_content: string;
    back_content: string;
    ka_name?: string;
  };
  onRate: (cardId: string, quality: number) => void;
  disabled?: boolean;
}

const qualityLevels = [
  { value: 0, label: 'Forgot', color: 'bg-red-600 hover:bg-red-700', description: 'Complete blackout' },
  { value: 1, label: 'Hard', color: 'bg-orange-600 hover:bg-orange-700', description: 'Incorrect but familiar' },
  { value: 2, label: 'Good', color: 'bg-yellow-600 hover:bg-yellow-700', description: 'Correct with hesitation' },
  { value: 3, label: 'Easy', color: 'bg-green-600 hover:bg-green-700', description: 'Perfect recall' },
];

export function ReviewCard({ card, onRate, disabled = false }: ReviewCardProps) {
  const [showAnswer, setShowAnswer] = useState(false);

  const handleRate = (quality: number) => {
    onRate(card.card_id, quality);
    setShowAnswer(false);
  };

  return (
    <Card className="max-w-2xl mx-auto">
      <CardHeader>
        {card.ka_name && (
          <div className="flex items-center gap-2 mb-2">
            <Star className="h-4 w-4 text-blue-600" />
            <span className="text-sm font-medium text-blue-600">{card.ka_name}</span>
          </div>
        )}
        <CardTitle className="text-lg">Review Card</CardTitle>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Front of Card */}
        <div className="rounded-lg bg-blue-50 border-2 border-blue-200 p-6">
          <p className="text-sm font-medium text-blue-900 mb-2">Question</p>
          <p className="text-gray-900 leading-relaxed">{card.front_content}</p>
        </div>

        {/* Show Answer Button */}
        {!showAnswer && (
          <Button
            onClick={() => setShowAnswer(true)}
            disabled={disabled}
            className="w-full"
            size="lg"
          >
            <Eye className="mr-2 h-5 w-5" />
            Show Answer
          </Button>
        )}

        {/* Back of Card */}
        {showAnswer && (
          <>
            <div className="rounded-lg bg-green-50 border-2 border-green-200 p-6">
              <p className="text-sm font-medium text-green-900 mb-2">Answer</p>
              <p className="text-gray-900 leading-relaxed">{card.back_content}</p>
            </div>

            {/* Quality Rating */}
            <div>
              <p className="text-sm font-medium text-gray-700 mb-3">
                How well did you remember this?
              </p>
              <div className="grid grid-cols-2 gap-3">
                {qualityLevels.map((level) => (
                  <button
                    key={level.value}
                    onClick={() => handleRate(level.value)}
                    disabled={disabled}
                    className={`${level.color} text-white px-4 py-3 rounded-lg transition-all disabled:opacity-50`}
                  >
                    <p className="font-semibold">{level.label}</p>
                    <p className="text-xs opacity-90">{level.description}</p>
                  </button>
                ))}
              </div>
            </div>
          </>
        )}
      </CardContent>
    </Card>
  );
}
