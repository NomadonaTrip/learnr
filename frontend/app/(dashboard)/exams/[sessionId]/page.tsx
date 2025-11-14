'use client';

import { useState, useEffect, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { QuestionCard } from '@/components/practice/QuestionCard';
import { ExamTimer } from '@/components/exams/ExamTimer';
import { AlertCircle, Flag, CheckCircle2 } from 'lucide-react';
import type { Question } from '@/types/api';

interface ExamPageProps {
  params: {
    sessionId: string;
  };
}

export default function ExamPage({ params }: ExamPageProps) {
  const router = useRouter();
  const [allQuestions, setAllQuestions] = useState<Question[]>([]);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [answers, setAnswers] = useState<Map<string, { choiceId: string; isCorrect: boolean }>>(
    new Map()
  );
  const [flaggedQuestions, setFlaggedQuestions] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');
  const [showSubmitConfirm, setShowSubmitConfirm] = useState(false);
  const hasAutoSubmitted = useRef(false);

  useEffect(() => {
    fetchExamQuestions();
  }, []);

  const fetchExamQuestions = async () => {
    try {
      setLoading(true);
      const response = await apiClient.get(`/v1/sessions/${params.sessionId}/questions`);
      setAllQuestions(response.data.questions);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load exam');
    } finally {
      setLoading(false);
    }
  };

  const handleAnswer = async (choiceId: string, isCorrect: boolean) => {
    const currentQuestion = allQuestions[currentQuestionIndex];

    try {
      await apiClient.post(`/v1/sessions/${params.sessionId}/answer`, {
        question_id: currentQuestion.question_id,
        selected_choice_id: choiceId,
      });

      setAnswers(new Map(answers.set(currentQuestion.question_id, { choiceId, isCorrect })));
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit answer');
    }
  };

  const handleNext = () => {
    if (currentQuestionIndex < allQuestions.length - 1) {
      setCurrentQuestionIndex(currentQuestionIndex + 1);
    }
  };

  const handlePrevious = () => {
    if (currentQuestionIndex > 0) {
      setCurrentQuestionIndex(currentQuestionIndex - 1);
    }
  };

  const handleJumpToQuestion = (index: number) => {
    setCurrentQuestionIndex(index);
  };

  const toggleFlag = () => {
    const newFlagged = new Set(flaggedQuestions);
    if (newFlagged.has(currentQuestionIndex)) {
      newFlagged.delete(currentQuestionIndex);
    } else {
      newFlagged.add(currentQuestionIndex);
    }
    setFlaggedQuestions(newFlagged);
  };

  const handleTimeUp = () => {
    if (!hasAutoSubmitted.current) {
      hasAutoSubmitted.current = true;
      handleSubmitExam(true);
    }
  };

  const handleSubmitExam = async (autoSubmit = false) => {
    setSubmitting(true);

    try {
      await apiClient.post(`/v1/sessions/${params.sessionId}/end`);
      router.push(`/exams/results/${params.sessionId}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to submit exam');
      setSubmitting(false);
    }
  };

  const answeredCount = answers.size;
  const unansweredCount = allQuestions.length - answeredCount;
  const currentQuestion = allQuestions[currentQuestionIndex];
  const isCurrentAnswered = currentQuestion && answers.has(currentQuestion.question_id);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading exam...</p>
        </div>
      </div>
    );
  }

  if (error && allQuestions.length === 0) {
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
              onClick={() => router.push('/exams')}
              className="mt-4"
              variant="outline"
            >
              Back to Exams
            </Button>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto">
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Main Content */}
        <div className="lg:col-span-3 space-y-6">
          {/* Timer */}
          <ExamTimer durationMinutes={210} onTimeUp={handleTimeUp} />

          {/* Question */}
          {currentQuestion && (
            <QuestionCard
              question={currentQuestion}
              questionNumber={currentQuestionIndex + 1}
              totalQuestions={allQuestions.length}
              onAnswer={handleAnswer}
              disabled={submitting}
            />
          )}

          {/* Navigation */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <Button
                  onClick={handlePrevious}
                  disabled={currentQuestionIndex === 0 || submitting}
                  variant="outline"
                >
                  Previous
                </Button>

                <div className="flex items-center gap-2">
                  <Button
                    onClick={toggleFlag}
                    variant={flaggedQuestions.has(currentQuestionIndex) ? 'default' : 'outline'}
                    disabled={submitting}
                  >
                    <Flag className="h-4 w-4 mr-2" />
                    {flaggedQuestions.has(currentQuestionIndex) ? 'Flagged' : 'Flag for Review'}
                  </Button>
                </div>

                <Button
                  onClick={handleNext}
                  disabled={currentQuestionIndex === allQuestions.length - 1 || submitting}
                >
                  Next
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="lg:col-span-1 space-y-4">
          {/* Progress Card */}
          <Card className="sticky top-4">
            <CardContent className="pt-6 space-y-4">
              <div>
                <p className="text-sm font-medium text-gray-700 mb-2">Progress</p>
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Answered</span>
                    <span className="font-semibold text-green-600">{answeredCount}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Remaining</span>
                    <span className="font-semibold text-gray-900">{unansweredCount}</span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Flagged</span>
                    <span className="font-semibold text-yellow-600">{flaggedQuestions.size}</span>
                  </div>
                </div>
              </div>

              <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-600 transition-all"
                  style={{ width: `${(answeredCount / allQuestions.length) * 100}%` }}
                />
              </div>

              <Button
                onClick={() => setShowSubmitConfirm(true)}
                disabled={submitting}
                className="w-full"
                variant={answeredCount === allQuestions.length ? 'default' : 'outline'}
              >
                {submitting ? 'Submitting...' : 'Submit Exam'}
              </Button>
            </CardContent>
          </Card>

          {/* Question Navigator */}
          <Card>
            <CardContent className="pt-6">
              <p className="text-sm font-medium text-gray-700 mb-3">Question Navigator</p>
              <div className="grid grid-cols-5 gap-2">
                {allQuestions.map((_, index) => {
                  const isAnswered = answers.has(allQuestions[index].question_id);
                  const isFlagged = flaggedQuestions.has(index);
                  const isCurrent = index === currentQuestionIndex;

                  return (
                    <button
                      key={index}
                      onClick={() => handleJumpToQuestion(index)}
                      className={`aspect-square rounded-md text-sm font-medium transition-all ${
                        isCurrent
                          ? 'ring-2 ring-blue-500 ring-offset-2'
                          : ''
                      } ${
                        isAnswered
                          ? 'bg-green-100 text-green-700 hover:bg-green-200'
                          : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                      } ${
                        isFlagged ? 'border-2 border-yellow-500' : ''
                      }`}
                    >
                      {index + 1}
                    </button>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Submit Confirmation Modal */}
      {showSubmitConfirm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <Card className="max-w-md w-full">
            <CardContent className="pt-6 space-y-4">
              <div className="text-center">
                <AlertCircle className="h-12 w-12 text-yellow-600 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  Submit Mock Exam?
                </h3>
                <p className="text-gray-600 mb-4">
                  {unansweredCount > 0 ? (
                    <>You have <span className="font-semibold">{unansweredCount} unanswered questions</span>. Are you sure you want to submit?</>
                  ) : (
                    'Are you ready to submit your exam?'
                  )}
                </p>
              </div>

              <div className="flex gap-3">
                <Button
                  onClick={() => setShowSubmitConfirm(false)}
                  variant="outline"
                  className="flex-1"
                >
                  Cancel
                </Button>
                <Button
                  onClick={() => handleSubmitExam(false)}
                  disabled={submitting}
                  className="flex-1"
                >
                  {submitting ? 'Submitting...' : 'Submit'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
