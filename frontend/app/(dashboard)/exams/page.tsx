'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  ClipboardCheck,
  Clock,
  FileQuestion,
  TrendingUp,
  AlertCircle,
  Trophy,
  Info
} from 'lucide-react';

export default function ExamsPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [examHistory, setExamHistory] = useState<any[]>([]);

  useEffect(() => {
    fetchExamHistory();
  }, []);

  const fetchExamHistory = async () => {
    try {
      const response = await apiClient.get('/v1/sessions', {
        params: {
          session_type: 'mock_exam',
          limit: 5,
        },
      });
      setExamHistory(response.data.sessions || []);
    } catch (err: any) {
      console.error('Failed to load exam history:', err);
    }
  };

  const handleStartExam = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post('/v1/exams/mock', {
        question_count: 100, // Standard CBAP exam length
      });

      router.push(`/exams/${response.data.session_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start mock exam');
      setLoading(false);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Mock Exams</h1>
        <p className="mt-1 text-gray-600">
          Simulate the real CBAP exam experience with full-length practice tests
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Exam Overview */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Questions</CardTitle>
            <FileQuestion className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">100</div>
            <p className="text-xs text-gray-500">Multiple choice questions</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Duration</CardTitle>
            <Clock className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">3.5 Hours</div>
            <p className="text-xs text-gray-500">210 minutes total</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Passing Score</CardTitle>
            <Trophy className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">70%</div>
            <p className="text-xs text-gray-500">CBAP passing threshold</p>
          </CardContent>
        </Card>
      </div>

      {/* Start Exam Section */}
      <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
        <CardHeader>
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-600">
              <ClipboardCheck className="h-6 w-6 text-white" />
            </div>
            <div className="flex-1">
              <CardTitle className="text-xl">Ready to Test Your Knowledge?</CardTitle>
              <CardDescription className="mt-1">
                Take a full-length CBAP mock exam to assess your readiness
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="rounded-lg bg-white/60 p-4">
            <div className="flex items-start gap-2">
              <Info className="h-5 w-5 text-blue-600 mt-0.5" />
              <div className="text-sm text-gray-700">
                <p className="font-medium mb-2">Before you start:</p>
                <ul className="space-y-1 list-disc list-inside">
                  <li>Ensure you have 3.5 hours of uninterrupted time</li>
                  <li>The exam will be automatically submitted when time expires</li>
                  <li>Questions are distributed across all 6 knowledge areas</li>
                  <li>You'll receive detailed performance analytics at the end</li>
                </ul>
              </div>
            </div>
          </div>

          <Button
            onClick={handleStartExam}
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-700"
            size="lg"
          >
            {loading ? 'Starting Mock Exam...' : 'Start Mock Exam'}
          </Button>
        </CardContent>
      </Card>

      {/* Recent Exams */}
      {examHistory.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Mock Exams</CardTitle>
            <CardDescription>Your previous exam attempts and scores</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {examHistory.map((exam) => {
                const score = exam.questions_attempted > 0
                  ? Math.round((exam.questions_correct / exam.questions_attempted) * 100)
                  : 0;
                const passed = score >= 70;

                return (
                  <div
                    key={exam.session_id}
                    className="flex items-center justify-between p-4 rounded-lg border border-gray-200 hover:bg-gray-50 transition-colors"
                  >
                    <div>
                      <p className="font-medium text-gray-900">
                        Mock Exam
                      </p>
                      <p className="text-sm text-gray-500">
                        {new Date(exam.created_at).toLocaleDateString()} •{' '}
                        {exam.questions_attempted} questions
                      </p>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className={`text-2xl font-bold ${
                          passed ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {score}%
                        </p>
                        <p className={`text-xs font-medium ${
                          passed ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {passed ? 'PASSED' : 'FAILED'}
                        </p>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => router.push(`/exams/results/${exam.session_id}`)}
                      >
                        View Results
                      </Button>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
