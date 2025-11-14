'use client';

import { Card, CardContent } from '@/components/ui/card';
import { CheckCircle2, XCircle, Circle } from 'lucide-react';

interface SessionProgressProps {
  currentQuestion: number;
  totalQuestions: number;
  correctCount: number;
  incorrectCount: number;
}

export function SessionProgress({
  currentQuestion,
  totalQuestions,
  correctCount,
  incorrectCount,
}: SessionProgressProps) {
  const accuracy =
    correctCount + incorrectCount > 0
      ? Math.round((correctCount / (correctCount + incorrectCount)) * 100)
      : 0;

  return (
    <Card>
      <CardContent className="pt-6">
        <div className="space-y-4">
          {/* Progress Bar */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-gray-700">Progress</span>
              <span className="text-sm text-gray-500">
                {currentQuestion} / {totalQuestions}
              </span>
            </div>
            <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all"
                style={{ width: `${(currentQuestion / totalQuestions) * 100}%` }}
              />
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{correctCount}</p>
              <p className="text-xs text-gray-500">Correct</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <XCircle className="h-5 w-5 text-red-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{incorrectCount}</p>
              <p className="text-xs text-gray-500">Incorrect</p>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-1">
                <Circle className="h-5 w-5 text-blue-600" />
              </div>
              <p className="text-2xl font-bold text-gray-900">{accuracy}%</p>
              <p className="text-xs text-gray-500">Accuracy</p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
