'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Trophy,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Target,
  Clock,
  Award
} from 'lucide-react';

interface ExamResultsPageProps {
  params: {
    sessionId: string;
  };
}

export default function ExamResultsPage({ params }: ExamResultsPageProps) {
  const router = useRouter();
  const [results, setResults] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchResults();
  }, []);

  const fetchResults = async () => {
    try {
      const response = await apiClient.get(`/v1/exams/${params.sessionId}/results`);
      setResults(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load results');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading results...</p>
        </div>
      </div>
    );
  }

  if (error || !results) {
    return (
      <div className="max-w-2xl mx-auto">
        <Card className="border-red-200 bg-red-50">
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <AlertCircle className="h-6 w-6 text-red-600" />
              <div>
                <p className="font-semibold text-red-900">Error</p>
                <p className="text-sm text-red-700">{error || 'Results not found'}</p>
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

  const overallScore = results.overall_score;
  const passed = results.passed;
  const passingScore = results.passing_score || 70;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="text-center">
        <div className="flex justify-center mb-4">
          <div className={`flex h-20 w-20 items-center justify-center rounded-full ${
            passed ? 'bg-green-100' : 'bg-red-100'
          }`}>
            {passed ? (
              <Trophy className="h-12 w-12 text-green-600" />
            ) : (
              <XCircle className="h-12 w-12 text-red-600" />
            )}
          </div>
        </div>
        <h1 className={`text-4xl font-bold ${passed ? 'text-green-900' : 'text-red-900'}`}>
          {passed ? 'Congratulations!' : 'Keep Practicing'}
        </h1>
        <p className="mt-2 text-gray-600">
          {passed
            ? 'You passed the mock exam! You\'re ready for the real CBAP exam.'
            : `You need ${passingScore}% to pass. Review your weak areas and try again.`}
        </p>
      </div>

      {/* Overall Score */}
      <Card className={`border-2 ${passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'}`}>
        <CardContent className="pt-6">
          <div className="text-center">
            <p className="text-sm font-medium text-gray-700 mb-2">Overall Score</p>
            <p className={`text-6xl font-bold ${passed ? 'text-green-600' : 'text-red-600'}`}>
              {overallScore}%
            </p>
            <p className="mt-2 text-sm text-gray-600">
              {results.questions_correct} correct out of {results.questions_attempted} questions
            </p>
            <div className="mt-4 h-3 w-full bg-gray-200 rounded-full overflow-hidden">
              <div
                className={`h-full ${passed ? 'bg-green-600' : 'bg-red-600'}`}
                style={{ width: `${overallScore}%` }}
              />
            </div>
            <div className="mt-2 flex justify-between text-xs text-gray-500">
              <span>0%</span>
              <span className="font-medium">Passing: {passingScore}%</span>
              <span>100%</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Questions</CardTitle>
            <Target className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{results.questions_attempted}</div>
            <p className="text-xs text-gray-500">Total answered</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Correct</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{results.questions_correct}</div>
            <p className="text-xs text-gray-500">{overallScore}% accuracy</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Incorrect</CardTitle>
            <XCircle className="h-4 w-4 text-red-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">
              {results.questions_attempted - results.questions_correct}
            </div>
            <p className="text-xs text-gray-500">
              {100 - overallScore}% missed
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Time Spent</CardTitle>
            <Clock className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {Math.floor(results.time_spent_minutes || 0)} min
            </div>
            <p className="text-xs text-gray-500">Of 210 minutes</p>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Area Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Performance by Knowledge Area</CardTitle>
          <CardDescription>
            Detailed breakdown of your performance across CBAP knowledge areas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {results.ka_performance?.map((ka: any) => {
              const kaScore = ka.attempted > 0
                ? Math.round((ka.correct / ka.attempted) * 100)
                : 0;
              const kaPassed = kaScore >= passingScore;

              return (
                <div key={ka.ka_id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <p className="text-sm font-medium text-gray-900">{ka.ka_name}</p>
                        {kaPassed ? (
                          <CheckCircle2 className="h-4 w-4 text-green-600" />
                        ) : (
                          <AlertCircle className="h-4 w-4 text-red-600" />
                        )}
                      </div>
                      <p className="text-xs text-gray-500">
                        {ka.correct}/{ka.attempted} correct
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-lg font-bold ${
                        kaPassed ? 'text-green-600' : 'text-red-600'
                      }`}>
                        {kaScore}%
                      </p>
                    </div>
                  </div>
                  <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full ${
                        kaPassed ? 'bg-green-600' : 'bg-red-600'
                      }`}
                      style={{ width: `${kaScore}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Recommendations */}
      {results.recommendations && results.recommendations.length > 0 && (
        <Card className="border-blue-200 bg-blue-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <TrendingUp className="h-5 w-5 text-blue-600" />
              Recommendations
            </CardTitle>
            <CardDescription>Next steps to improve your performance</CardDescription>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {results.recommendations.map((rec: string, index: number) => (
                <li key={index} className="flex items-start gap-2 text-sm text-gray-700">
                  <Award className="h-4 w-4 text-blue-600 mt-0.5" />
                  {rec}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Actions */}
      <div className="flex gap-4">
        <Button
          onClick={() => router.push('/exams')}
          className="flex-1"
        >
          Take Another Exam
        </Button>
        <Button
          onClick={() => router.push('/content')}
          variant="outline"
          className="flex-1"
        >
          Study Weak Areas
        </Button>
        <Button
          onClick={() => router.push('/dashboard')}
          variant="outline"
          className="flex-1"
        >
          Back to Dashboard
        </Button>
      </div>
    </div>
  );
}
