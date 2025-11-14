'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { QuestionCard } from '@/components/practice/QuestionCard';
import { SessionProgress } from '@/components/practice/SessionProgress';
import { AlertCircle, ArrowRight, CheckCircle2, TrendingUp } from 'lucide-react';
import type { Question, SessionSummary } from '@/types/api';

interface SessionPageProps {
  params: {
    sessionId: string;
  };
}

export default function SessionPage({ params }: SessionPageProps) {
  const router = useRouter();
  const [currentQuestion, setCurrentQuestion] = useState<Question | null>(null);
  const [questionNumber, setQuestionNumber] = useState(1);
  const [totalQuestions, setTotalQuestions] = useState(0);
  const [correctCount, setCorrectCount] = useState(0);
  const [incorrectCount, setIncorrectCount] = useState(0);
  const [sessionComplete, setSessionComplete] = useState(false);
  const [sessionSummary, setSessionSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [answeredCurrentQuestion, setAnsweredCurrentQuestion] = useState(false);

  useEffect(() => {
    fetchNextQuestion();
  }, []);

  const fetchNextQuestion = async () => {
    try {
      setLoading(true);
      setAnsweredCurrentQuestion(false);

      const response = await apiClient.get(
        `/v1/sessions/${params.sessionId}/next-question`
      );

      if (response.data.session_complete) {
        // Session is complete, fetch summary
        const summaryResponse = await apiClient.get(
          `/v1/sessions/${params.sessionId}/summary`
        );
        setSessionSummary(summaryResponse.data);
        setSessionComplete(true);
      } else {
        setCurrentQuestion(response.data.question);
        setQuestionNumber(response.data.current_question_number);
        setTotalQuestions(response.data.total_questions);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load question');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = async (choiceId: string, isCorrect: boolean) => {
    try {
      await apiClient.post(`/v1/sessions/${params.sessionId}/answer`, {
        question_id: currentQuestion?.question_id,
        selected_choice_id: choiceId,
      });

      if (isCorrect) {
        setCorrectCount((prev) => prev + 1);
      } else {
        setIncorrectCount((prev) => prev + 1);
      }

      setAnsweredCurrentQuestion(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit answer');
    }
  };

  const handleNext = () => {
    fetchNextQuestion();
  };

  const handleEndSession = async () => {
    try {
      await apiClient.post(`/v1/sessions/${params.sessionId}/end`);
      router.push('/dashboard');
    } catch (err: any) {
      console.error('Failed to end session:', err);
      router.push('/dashboard');
    }
  };

  if (loading && !currentQuestion) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading question...</p>
        </div>
      </div>
    );
  }

  if (error && !currentQuestion) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            </div>
            <Button
              onClick={() => router.push('/practice')}
              className="mt-4"
              variant="outline"
            >
              Back to Practice
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  if (sessionComplete && sessionSummary) {
    const accuracy = sessionSummary.questions_attempted > 0
      ? Math.round((sessionSummary.questions_correct / sessionSummary.questions_attempted) * 100)
      : 0;

    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="text-center">
          <div className="flex justify-center mb-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100">
              <CheckCircle2 className="h-10 w-10 text-green-600" />
            </div>
          </div>
          <h1 className="text-3xl font-bold text-gray-900">Session Complete!</h1>
          <p className="mt-2 text-gray-600">Great job! Here's how you performed</p>
        </div>

        {/* Summary Stats */}
        <div className="grid gap-6 md:grid-cols-3">
          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Questions Answered
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-gray-900">
                {sessionSummary.questions_attempted}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Correct Answers
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-green-600">
                {sessionSummary.questions_correct}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-sm font-medium text-gray-500">
                Accuracy
              </CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-3xl font-bold text-blue-600">{accuracy}%</p>
            </CardContent>
          </Card>
        </div>

        {/* Knowledge Area Breakdown */}
        {sessionSummary.ka_performance && sessionSummary.ka_performance.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle>Performance by Knowledge Area</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {sessionSummary.ka_performance.map((ka: any) => {
                  const kaAccuracy = ka.attempted > 0
                    ? Math.round((ka.correct / ka.attempted) * 100)
                    : 0;

                  return (
                    <div key={ka.ka_id} className="space-y-2">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-medium text-gray-900">{ka.ka_name}</p>
                        <p className="text-sm text-gray-600">
                          {ka.correct}/{ka.attempted} ({kaAccuracy}%)
                        </p>
                      </div>
                      <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full ${
                            kaAccuracy >= 70
                              ? 'bg-green-600'
                              : kaAccuracy >= 50
                              ? 'bg-yellow-600'
                              : 'bg-red-600'
                          }`}
                          style={{ width: `${kaAccuracy}%` }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Actions */}
        <div className="flex gap-4">
          <Button onClick={() => router.push('/practice')} className="flex-1">
            Start New Session
          </Button>
          <Button onClick={handleEndSession} variant="outline" className="flex-1">
            Back to Dashboard
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Progress */}
      <SessionProgress
        currentQuestion={questionNumber}
        totalQuestions={totalQuestions}
        correctCount={correctCount}
        incorrectCount={incorrectCount}
      />

      {/* Question */}
      {currentQuestion && (
        <QuestionCard
          question={currentQuestion}
          questionNumber={questionNumber}
          totalQuestions={totalQuestions}
          onAnswer={handleAnswer}
          disabled={loading}
        />
      )}

      {/* Next Button */}
      {answeredCurrentQuestion && (
        <div className="flex justify-end">
          <Button onClick={handleNext} disabled={loading}>
            {loading ? 'Loading...' : 'Next Question'}
            <ArrowRight className="ml-2 h-4 w-4" />
          </Button>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="text-sm">{error}</p>
        </div>
      )}
    </div>
  );
}
