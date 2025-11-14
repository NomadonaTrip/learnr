'use client';

import { useEffect, useState } from 'react';
import { useAuthStore } from '@/lib/store/auth-store';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  Brain,
  BookOpen,
  ClipboardCheck,
  TrendingUp,
  Calendar,
  ArrowRight,
  Trophy,
  Target,
  Zap
} from 'lucide-react';
import Link from 'next/link';
import type { DashboardData, KnowledgeAreaProgress } from '@/types/api';

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const [dashboardData, setDashboardData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchDashboard() {
      try {
        const response = await apiClient.get<DashboardData>('/v1/dashboard');
        setDashboardData(response.data);
      } catch (err: any) {
        setError(err.response?.data?.detail || 'Failed to load dashboard');
      } finally {
        setLoading(false);
      }
    }

    fetchDashboard();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
          <p className="text-gray-600">Loading your progress...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg bg-red-50 p-4 text-red-600">
        <p className="font-medium">Error loading dashboard</p>
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  const overallCompetency = dashboardData?.overall_competency || 0;
  const competencyPercentage = Math.round(overallCompetency * 100);
  const dueCards = dashboardData?.spaced_repetition_summary.due_cards_count || 0;

  return (
    <div className="space-y-6">
      {/* Welcome Section */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Your Learning Dashboard</h1>
        <p className="mt-1 text-gray-600">
          Track your progress and continue your CBAP certification journey
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {/* Overall Competency */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Overall Competency</CardTitle>
            <Trophy className="h-4 w-4 text-yellow-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{competencyPercentage}%</div>
            <div className="mt-2 h-2 w-full bg-gray-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-600 to-indigo-600 transition-all"
                style={{ width: `${competencyPercentage}%` }}
              />
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {overallCompetency >= 0.7 ? 'Excellent progress!' : 'Keep practicing!'}
            </p>
          </CardContent>
        </Card>

        {/* Questions Answered */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Questions Answered</CardTitle>
            <Brain className="h-4 w-4 text-blue-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.total_questions_attempted || 0}
            </div>
            <p className="mt-2 text-xs text-gray-500">
              {dashboardData?.questions_correct || 0} correct (
              {dashboardData?.total_questions_attempted
                ? Math.round(
                    ((dashboardData.questions_correct || 0) / dashboardData.total_questions_attempted) * 100
                  )
                : 0}
              %)
            </p>
          </CardContent>
        </Card>

        {/* Study Streak */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Study Streak</CardTitle>
            <Zap className="h-4 w-4 text-orange-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dashboardData?.current_streak || 0} days
            </div>
            <p className="mt-2 text-xs text-gray-500">
              Longest: {dashboardData?.longest_streak || 0} days
            </p>
          </CardContent>
        </Card>

        {/* Due Reviews */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Due Reviews</CardTitle>
            <Calendar className="h-4 w-4 text-green-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dueCards}</div>
            <p className="mt-2 text-xs text-gray-500">
              {dueCards > 0 ? 'Cards ready for review' : 'All caught up!'}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Knowledge Areas Progress */}
      <Card>
        <CardHeader>
          <CardTitle>Knowledge Area Progress</CardTitle>
          <CardDescription>Your competency across CBAP knowledge areas</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {dashboardData?.knowledge_areas?.map((ka: KnowledgeAreaProgress) => {
              const competency = Math.round(ka.competency_score * 100);

              return (
                <div key={ka.ka_id} className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-900">{ka.ka_name}</p>
                      <p className="text-xs text-gray-500">
                        {ka.questions_attempted} questions • {ka.questions_correct} correct
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-bold text-gray-900">{competency}%</p>
                      <p className="text-xs text-gray-500">
                        {ka.weight_percentage}% of exam
                      </p>
                    </div>
                  </div>
                  <div className="h-2 w-full bg-gray-200 rounded-full overflow-hidden">
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
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>

      {/* Quick Actions */}
      <div className="grid gap-6 md:grid-cols-3">
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <Brain className="h-8 w-8 text-blue-600 mb-2" />
            <CardTitle>Practice Questions</CardTitle>
            <CardDescription>
              Start an adaptive practice session tailored to your level
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/practice">
              <Button className="w-full">
                Start Practice
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <ClipboardCheck className="h-8 w-8 text-purple-600 mb-2" />
            <CardTitle>Mock Exam</CardTitle>
            <CardDescription>
              Take a full-length practice exam to test your knowledge
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/exams">
              <Button className="w-full" variant="outline">
                Start Exam
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <BookOpen className="h-8 w-8 text-green-600 mb-2" />
            <CardTitle>Study Materials</CardTitle>
            <CardDescription>
              Review recommended content based on your performance
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/content">
              <Button className="w-full" variant="outline">
                View Content
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Due Reviews Alert */}
      {dueCards > 0 && (
        <Card className="border-green-200 bg-green-50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <Calendar className="h-5 w-5 text-green-600" />
              <CardTitle className="text-green-900">
                {dueCards} Review {dueCards === 1 ? 'Card' : 'Cards'} Due
              </CardTitle>
            </div>
            <CardDescription className="text-green-700">
              Review your spaced repetition cards to maintain your knowledge
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/reviews">
              <Button className="bg-green-600 hover:bg-green-700">
                Review Now
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
