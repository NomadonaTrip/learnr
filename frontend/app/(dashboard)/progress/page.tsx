'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import {
  TrendingUp,
  Target,
  Calendar,
  Trophy,
  BookOpen,
  Brain,
  AlertCircle,
  CheckCircle2,
  Award
} from 'lucide-react';
import type { DashboardData } from '@/types/api';

export default function ProgressPage() {
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    fetchProgressData();
  }, []);

  const fetchProgressData = async () => {
    try {
      const response = await apiClient.get<DashboardData>('/v1/dashboard');
      setDashboardData(response.data);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load progress data');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-600">
        <div className="flex items-center gap-2">
          <AlertCircle className="h-5 w-5" />
          <p className="font-medium">Error loading progress</p>
        </div>
        <p className="text-sm mt-1">{error}</p>
      </div>
    );
  }

  const overallCompetency = dashboardData?.overall_competency || 0;
  const competencyPercentage = Math.round(overallCompetency * 100);

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Your Progress</h1>
        <p className="mt-1 text-gray-600">
          Track your learning journey and exam readiness
        </p>
      </div>

      {/* Overall Readiness */}
      <Card className="border-blue-200 bg-gradient-to-br from-blue-50 to-indigo-50">
        <CardHeader>
          <CardTitle className="text-2xl">Exam Readiness</CardTitle>
          <CardDescription>Your overall competency level</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center">
              <div className="relative inline-flex items-center justify-center">
                <svg className="w-40 h-40 transform -rotate-90">
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    className="text-gray-200"
                  />
                  <circle
                    cx="80"
                    cy="80"
                    r="70"
                    stroke="currentColor"
                    strokeWidth="12"
                    fill="none"
                    strokeDasharray={`${2 * Math.PI * 70}`}
                    strokeDashoffset={`${2 * Math.PI * 70 * (1 - competencyPercentage / 100)}`}
                    className={`${
                      competencyPercentage >= 70
                        ? 'text-green-600'
                        : competencyPercentage >= 50
                        ? 'text-yellow-600'
                        : 'text-red-600'
                    } transition-all duration-1000`}
                    strokeLinecap="round"
                  />
                </svg>
                <div className="absolute">
                  <p className="text-4xl font-bold text-gray-900">{competencyPercentage}%</p>
                  <p className="text-sm text-gray-600">Ready</p>
                </div>
              </div>
              <p className="mt-4 text-gray-700">
                {competencyPercentage >= 70
                  ? 'You\'re ready to take the exam!'
                  : competencyPercentage >= 50
                  ? 'Keep practicing to reach exam readiness'
                  : 'Continue building your knowledge'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Questions</CardTitle>
            <Brain className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.total_questions_attempted || 0}
            </div>
            <p className="text-xs text-gray-500">
              {dashboardData?.questions_correct || 0} correct
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Accuracy</CardTitle>
            <Target className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.total_questions_attempted
                ? Math.round(
                    ((dashboardData.questions_correct || 0) / dashboardData.total_questions_attempted) * 100
                  )
                : 0}
              %
            </div>
            <p className="text-xs text-gray-500">Overall accuracy</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Streak</CardTitle>
            <Trophy className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.current_streak || 0}
            </div>
            <p className="text-xs text-gray-500">
              Days in a row
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Due Reviews</CardTitle>
            <Calendar className="h-4 w-4 text-purple-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.spaced_repetition_summary?.due_cards_count || 0}
            </div>
            <p className="text-xs text-gray-500">Cards to review</p>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Area Details */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Area Mastery</CardTitle>
          <CardDescription>
            Detailed breakdown of your competency across all 6 CBAP knowledge areas
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {dashboardData?.knowledge_areas?.map((ka, index) => {
              const competency = Math.round(ka.competency_score * 100);
              const isMastered = competency >= 70;
              const accuracy = ka.questions_attempted > 0
                ? Math.round((ka.questions_correct / ka.questions_attempted) * 100)
                : 0;

              return (
                <div key={ka.ka_id} className="space-y-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <h3 className="font-semibold text-gray-900">{ka.ka_name}</h3>
                        {isMastered && (
                          <CheckCircle2 className="h-5 w-5 text-green-600" />
                        )}
                      </div>
                      <p className="text-sm text-gray-600 mt-1">
                        Weight: {ka.weight_percentage}% of exam
                      </p>
                    </div>
                    <div className="text-right">
                      <p className={`text-2xl font-bold ${
                        competency >= 70
                          ? 'text-green-600'
                          : competency >= 50
                          ? 'text-yellow-600'
                          : 'text-red-600'
                      }`}>
                        {competency}%
                      </p>
                      <p className="text-xs text-gray-500">Competency</p>
                    </div>
                  </div>

                  <div className="h-3 w-full bg-gray-200 rounded-full overflow-hidden">
                    <div
                      className={`h-full transition-all ${
                        competency >= 70
                          ? 'bg-green-600'
                          : competency >= 50
                          ? 'bg-yellow-600'
                          : 'bg-red-600'
                      }`}
                      style={{ width: `${competency}%` }}
                    />
                  </div>

                  <div className="grid grid-cols-3 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Questions</p>
                      <p className="font-semibold text-gray-900">{ka.questions_attempted}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Correct</p>
                      <p className="font-semibold text-green-600">{ka.questions_correct}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Accuracy</p>
                      <p className="font-semibold text-blue-600">{accuracy}%</p>
                    </div>
                  </div>

                  {index < (dashboardData?.knowledge_areas?.length || 0) - 1 && (
                    <div className="border-b border-gray-200 pt-3" />
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Achievement Badges */}
      <Card className="border-yellow-200 bg-yellow-50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Award className="h-5 w-5 text-yellow-600" />
            Achievements
          </CardTitle>
          <CardDescription>Milestones you've reached</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            {dashboardData && dashboardData.total_questions_attempted >= 100 && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-white border border-yellow-200">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                  <Brain className="h-6 w-6 text-yellow-600" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">Century</p>
                  <p className="text-xs text-gray-600">100+ questions answered</p>
                </div>
              </div>
            )}

            {dashboardData && dashboardData.current_streak >= 7 && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-white border border-yellow-200">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                  <Trophy className="h-6 w-6 text-yellow-600" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">Dedicated</p>
                  <p className="text-xs text-gray-600">7 day streak</p>
                </div>
              </div>
            )}

            {competencyPercentage >= 70 && (
              <div className="flex items-center gap-3 p-3 rounded-lg bg-white border border-yellow-200">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-yellow-100">
                  <CheckCircle2 className="h-6 w-6 text-yellow-600" />
                </div>
                <div>
                  <p className="font-semibold text-gray-900">Exam Ready</p>
                  <p className="text-xs text-gray-600">70%+ overall competency</p>
                </div>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
