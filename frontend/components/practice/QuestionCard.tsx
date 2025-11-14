'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { CheckCircle2, XCircle, AlertCircle } from 'lucide-react';
import type { Question, AnswerChoice } from '@/types/api';

interface QuestionCardProps {
  question: Question;
  questionNumber: number;
  totalQuestions: number;
  onAnswer: (choiceId: string, isCorrect: boolean) => void;
  disabled?: boolean;
}

export function QuestionCard({
  question,
  questionNumber,
  totalQuestions,
  onAnswer,
  disabled = false,
}: QuestionCardProps) {
  const [selectedChoice, setSelectedChoice] = useState<string | null>(null);
  const [hasAnswered, setHasAnswered] = useState(false);
  const [isCorrect, setIsCorrect] = useState<boolean | null>(null);

  const handleChoiceClick = (choice: AnswerChoice) => {
    if (hasAnswered || disabled) return;
    setSelectedChoice(choice.choice_id);
  };

  const handleSubmit = () => {
    if (!selectedChoice || hasAnswered) return;

    const choice = question.answer_choices.find((c) => c.choice_id === selectedChoice);
    if (!choice) return;

    const correct = choice.is_correct;
    setIsCorrect(correct);
    setHasAnswered(true);
    onAnswer(selectedChoice, correct);
  };

  const getChoiceClassName = (choice: AnswerChoice) => {
    const baseClass = 'w-full text-left p-4 rounded-lg border-2 transition-all';

    if (!hasAnswered) {
      if (selectedChoice === choice.choice_id) {
        return `${baseClass} border-blue-500 bg-blue-50`;
      }
      return `${baseClass} border-gray-200 hover:border-blue-300 hover:bg-gray-50`;
    }

    // After answering
    if (choice.is_correct) {
      return `${baseClass} border-green-500 bg-green-50`;
    }

    if (selectedChoice === choice.choice_id && !choice.is_correct) {
      return `${baseClass} border-red-500 bg-red-50`;
    }

    return `${baseClass} border-gray-200 bg-gray-50 opacity-50`;
  };

  const getChoiceIcon = (choice: AnswerChoice) => {
    if (!hasAnswered) return null;

    if (choice.is_correct) {
      return <CheckCircle2 className="h-5 w-5 text-green-600" />;
    }

    if (selectedChoice === choice.choice_id && !choice.is_correct) {
      return <XCircle className="h-5 w-5 text-red-600" />;
    }

    return null;
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-500">
              Question {questionNumber} of {totalQuestions}
            </span>
            <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
              {question.difficulty_label || 'Medium'}
            </span>
          </div>
          <span className="text-xs text-gray-500">{question.ka_name}</span>
        </div>
        <CardTitle className="mt-4 text-lg font-semibold leading-relaxed">
          {question.question_text}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3">
        {question.answer_choices.map((choice) => (
          <button
            key={choice.choice_id}
            onClick={() => handleChoiceClick(choice)}
            disabled={hasAnswered || disabled}
            className={getChoiceClassName(choice)}
          >
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">{choice.choice_text}</span>
              {getChoiceIcon(choice)}
            </div>
          </button>
        ))}

        {!hasAnswered && (
          <Button
            onClick={handleSubmit}
            disabled={!selectedChoice || disabled}
            className="w-full mt-4"
          >
            Submit Answer
          </Button>
        )}

        {hasAnswered && (
          <div
            className={`mt-4 rounded-lg p-4 ${
              isCorrect ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'
            }`}
          >
            <div className="flex items-start gap-3">
              {isCorrect ? (
                <CheckCircle2 className="h-5 w-5 text-green-600 mt-0.5" />
              ) : (
                <XCircle className="h-5 w-5 text-red-600 mt-0.5" />
              )}
              <div>
                <p className={`font-semibold ${isCorrect ? 'text-green-900' : 'text-red-900'}`}>
                  {isCorrect ? 'Correct!' : 'Incorrect'}
                </p>
                {question.explanation && (
                  <p className={`mt-2 text-sm ${isCorrect ? 'text-green-800' : 'text-red-800'}`}>
                    <span className="font-medium">Explanation:</span> {question.explanation}
                  </p>
                )}
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
