'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { ReviewCard } from '@/components/reviews/ReviewCard';
import {
  Calendar,
  CheckCircle2,
  Clock,
  TrendingUp,
  AlertCircle,
  Trophy,
  RefreshCw
} from 'lucide-react';

export default function ReviewsPage() {
  const [dueCards, setDueCards] = useState<any[]>([]);
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [reviewedCount, setReviewedCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [sessionComplete, setSessionComplete] = useState(false);

  useEffect(() => {
    fetchDueCards();
  }, []);

  const fetchDueCards = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get('/v1/reviews/due');
      setDueCards(response.data.cards || []);

      if (response.data.cards?.length === 0) {
        setSessionComplete(true);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load review cards');
    } finally {
      setLoading(false);
    }
  };

  const handleRateCard = async (cardId: string, quality: number) => {
    setSubmitting(true);

    try {
      await apiClient.post('/v1/reviews/rate', {
        card_id: cardId,
        quality,
      });

      setReviewedCount((prev) => prev + 1);

      if (currentCardIndex < dueCards.length - 1) {
        setCurrentCardIndex((prev) => prev + 1);
      } else {
        setSessionComplete(true);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to rate card');
    } finally {
      setSubmitting(false);
    }
  };

  const handleStartNewSession = () => {
    setCurrentCardIndex(0);
    setReviewedCount(0);
    setSessionComplete(false);
    fetchDueCards();
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading review cards...</p>
        </div>
      </div>
    );
  }

  if (sessionComplete || dueCards.length === 0) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle2 className="h-10 w-10 text-green-600" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">
            {reviewedCount > 0 ? 'Review Complete!' : 'All Caught Up!'}
          </h1>
          <p className="mt-2 text-gray-600">
            {reviewedCount > 0
              ? `You reviewed ${reviewedCount} ${reviewedCount === 1 ? 'card' : 'cards'} today`
              : 'No cards are due for review right now'}
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>What's Next?</CardTitle>
            <CardDescription>Continue your learning journey</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={handleStartNewSession}
              variant="outline"
              className="w-full"
            >
              <RefreshCw className="mr-2 h-4 w-4" />
              Check for New Cards
            </Button>
            <Button
              onClick={() => window.location.href = '/practice'}
              className="w-full"
            >
              Start Practice Session
            </Button>
            <Button
              onClick={() => window.location.href = '/dashboard'}
              variant="outline"
              className="w-full"
            >
              Back to Dashboard
            </Button>
          </CardContent>
        </Card>

        {reviewedCount > 0 && (
          <Card className="border-blue-200 bg-blue-50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-3">
                <Trophy className="h-8 w-8 text-blue-600" />
                <div>
                  <p className="font-semibold text-blue-900">Great job!</p>
                  <p className="text-sm text-blue-700">
                    Consistent review helps solidify your knowledge
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    );
  }

  const currentCard = dueCards[currentCardIndex];
  const remainingCards = dueCards.length - currentCardIndex;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Spaced Repetition Review</h1>
        <p className="mt-1 text-gray-600">
          Review your cards to maintain long-term retention
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Progress */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Reviewed</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{reviewedCount}</div>
            <p className="text-xs text-gray-500">Cards completed</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Remaining</CardTitle>
            <Clock className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">{remainingCards}</div>
            <p className="text-xs text-gray-500">Cards left to review</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Progress</CardTitle>
            <TrendingUp className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">
              {Math.round((reviewedCount / dueCards.length) * 100)}%
            </div>
            <p className="text-xs text-gray-500">Session progress</p>
          </CardContent>
        </Card>
      </div>

      {/* Progress Bar */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-700">Session Progress</span>
            <span className="text-sm text-gray-500">
              {currentCardIndex + 1} / {dueCards.length}
            </span>
          </div>
          <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all"
              style={{ width: `${((currentCardIndex + 1) / dueCards.length) * 100}%` }}
            />
          </div>
        </CardContent>
      </Card>

      {/* Current Card */}
      {currentCard && (
        <ReviewCard
          card={currentCard}
          onRate={handleRateCard}
          disabled={submitting}
        />
      )}
    </div>
  );
}
