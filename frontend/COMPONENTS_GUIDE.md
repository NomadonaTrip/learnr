# Component Implementation Guide

Quick reference for building LearnR frontend components.

## 🎯 Authentication Components

### Login Page
**Location:** `app/(auth)/login/page.tsx`

```tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import apiClient, { handleApiError } from '@/lib/api-client';

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
});

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const form = useForm({
    resolver: zodResolver(loginSchema),
    defaultValues: { email: '', password: '' },
  });

  const onSubmit = async (data: z.infer<typeof loginSchema>) => {
    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post('/auth/login', data);
      const { access_token, refresh_token } = response.data;

      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);

      router.push('/dashboard');
    } catch (err) {
      setError(handleApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center">
      <form onSubmit={form.handleSubmit(onSubmit)} className="w-full max-w-md space-y-4 p-8">
        <h1 className="text-2xl font-bold">Login to LearnR</h1>

        {error && <div className="text-red-600 text-sm">{error}</div>}

        <div>
          <Label htmlFor="email">Email</Label>
          <Input {...form.register('email')} type="email" />
          {form.formState.errors.email && (
            <p className="text-red-600 text-sm">{form.formState.errors.email.message}</p>
          )}
        </div>

        <div>
          <Label htmlFor="password">Password</Label>
          <Input {...form.register('password')} type="password" />
          {form.formState.errors.password && (
            <p className="text-red-600 text-sm">{form.formState.errors.password.message}</p>
          )}
        </div>

        <Button type="submit" className="w-full" disabled={loading}>
          {loading ? 'Logging in...' : 'Login'}
        </Button>
      </form>
    </div>
  );
}
```

---

## 📊 Dashboard Components

### Dashboard Layout
**Location:** `app/(dashboard)/layout.tsx`

```tsx
import Sidebar from '@/components/shared/Sidebar';
import Header from '@/components/shared/Header';

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-screen">
      <Sidebar />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Header />
        <main className="flex-1 overflow-y-auto p-6 bg-gray-50">
          {children}
        </main>
      </div>
    </div>
  );
}
```

### Progress Card Component
**Location:** `components/dashboard/ProgressCard.tsx`

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';

interface ProgressCardProps {
  score: number;
  questionsToday: number;
  streak: number;
}

export function ProgressCard({ score, questionsToday, streak }: ProgressCardProps) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Overall Progress</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div>
          <div className="text-4xl font-bold text-blue-600">{score.toFixed(1)}%</div>
          <p className="text-sm text-gray-600">Overall Competency</p>
          <Progress value={score} className="mt-2" />
        </div>

        <div className="grid grid-cols-2 gap-4 pt-4 border-t">
          <div>
            <div className="text-2xl font-semibold">{questionsToday}</div>
            <p className="text-xs text-gray-600">Questions Today</p>
          </div>
          <div>
            <div className="text-2xl font-semibold">{streak}</div>
            <p className="text-xs text-gray-600">Day Streak 🔥</p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
```

---

## ❓ Practice Session Components

### Question Display
**Location:** `components/practice/QuestionDisplay.tsx`

```tsx
'use client';

import { useState } from 'react';
import { Button } from '@/components/ui/button';
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group';
import { Label } from '@/components/ui/label';
import { Question } from '@/types/api';

interface QuestionDisplayProps {
  question: Question;
  onSubmit: (choiceId: string) => void;
  questionNumber: number;
  totalQuestions: number;
}

export function QuestionDisplay({
  question,
  onSubmit,
  questionNumber,
  totalQuestions
}: QuestionDisplayProps) {
  const [selectedChoice, setSelectedChoice] = useState('');

  const handleSubmit = () => {
    if (selectedChoice) {
      onSubmit(selectedChoice);
      setSelectedChoice('');
    }
  };

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="flex justify-between text-sm text-gray-600">
        <span>Question {questionNumber} of {totalQuestions}</span>
        <span>KA: {question.ka_name}</span>
      </div>

      {/* Question */}
      <div className="text-lg font-medium leading-relaxed">
        {question.question_text}
      </div>

      {/* Choices */}
      <RadioGroup value={selectedChoice} onValueChange={setSelectedChoice}>
        <div className="space-y-3">
          {question.answer_choices
            .sort((a, b) => a.choice_order - b.choice_order)
            .map((choice, index) => (
              <div
                key={choice.choice_id}
                className="flex items-center space-x-3 p-4 border rounded-lg hover:bg-gray-50 cursor-pointer"
              >
                <RadioGroupItem value={choice.choice_id} id={choice.choice_id} />
                <Label
                  htmlFor={choice.choice_id}
                  className="flex-1 cursor-pointer"
                >
                  <span className="font-semibold mr-2">
                    {String.fromCharCode(65 + index)}.
                  </span>
                  {choice.choice_text}
                </Label>
              </div>
            ))}
        </div>
      </RadioGroup>

      {/* Submit */}
      <Button
        onClick={handleSubmit}
        disabled={!selectedChoice}
        className="w-full"
        size="lg"
      >
        Submit Answer
      </Button>
    </div>
  );
}
```

---

## 📚 Content Components

### Content Card
**Location:** `components/recommendations/ContentCard.tsx`

```tsx
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { BookOpen, Star } from 'lucide-react';
import { ContentChunk } from '@/types/api';

interface ContentCardProps {
  content: ContentChunk;
  onClick: () => void;
}

export function ContentCard({ content, onClick }: ContentCardProps) {
  return (
    <Card className="hover:shadow-md transition-shadow cursor-pointer" onClick={onClick}>
      <CardContent className="p-6 space-y-3">
        <div className="flex items-start justify-between">
          <h3 className="font-semibold text-lg">{content.content_title}</h3>
          {content.difficulty_level && (
            <Badge variant={
              content.difficulty_level === 'basic' ? 'secondary' :
              content.difficulty_level === 'intermediate' ? 'default' :
              'destructive'
            }>
              {content.difficulty_level}
            </Badge>
          )}
        </div>

        <p className="text-sm text-gray-600 line-clamp-2">
          {content.content_text}
        </p>

        <div className="flex items-center justify-between text-sm text-gray-500">
          <div className="flex items-center gap-2">
            <BookOpen className="h-4 w-4" />
            {content.source_document && (
              <span>{content.source_document} {content.source_page}</span>
            )}
          </div>

          {content.helpfulness_score && (
            <div className="flex items-center gap-1">
              <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
              <span>{content.helpfulness_score}%</span>
            </div>
          )}
        </div>

        {content.expert_reviewed && (
          <Badge variant="outline" className="text-xs">
            ✓ Expert Reviewed
          </Badge>
        )}
      </CardContent>
    </Card>
  );
}
```

---

## 🎓 Mock Exam Components

### Exam Results Display
**Location:** `components/exam/ResultsDisplay.tsx`

```tsx
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { CheckCircle2, XCircle } from 'lucide-react';
import { MockExamResultsResponse } from '@/types/api';
import { formatDuration } from '@/lib/utils';

interface ResultsDisplayProps {
  results: MockExamResultsResponse;
}

export function ResultsDisplay({ results }: ResultsDisplayProps) {
  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card className={results.passed ? 'border-green-500' : 'border-red-500'}>
        <CardContent className="pt-6">
          <div className="text-center space-y-4">
            {results.passed ? (
              <CheckCircle2 className="h-16 w-16 text-green-500 mx-auto" />
            ) : (
              <XCircle className="h-16 w-16 text-red-500 mx-auto" />
            )}

            <div>
              <div className="text-5xl font-bold">
                {results.score_percentage.toFixed(1)}%
              </div>
              <p className="text-gray-600 mt-2">
                {results.passed ? 'Congratulations! You Passed!' : 'Keep Studying!'}
              </p>
            </div>

            <div className="text-sm text-gray-600">
              Passing Score: {results.passing_score}%
              <span className="mx-2">•</span>
              Margin: {results.margin > 0 ? '+' : ''}{results.margin.toFixed(1)}%
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics */}
      <div className="grid grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-green-600">
              {results.correct_answers}
            </div>
            <p className="text-sm text-gray-600">Correct</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-red-600">
              {results.incorrect_answers}
            </div>
            <p className="text-sm text-gray-600">Incorrect</p>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="pt-6 text-center">
            <div className="text-3xl font-bold text-blue-600">
              {formatDuration(results.duration_seconds)}
            </div>
            <p className="text-sm text-gray-600">Time Taken</p>
          </CardContent>
        </Card>
      </div>

      {/* KA Performance */}
      <Card>
        <CardHeader>
          <CardTitle>Performance by Knowledge Area</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {results.performance_by_ka.map((ka) => (
            <div key={ka.ka_id} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span>{ka.ka_name}</span>
                <span className="font-semibold">
                  {ka.score_percentage.toFixed(1)}%
                </span>
              </div>
              <Progress value={ka.score_percentage} className="h-2" />
              <div className="text-xs text-gray-500">
                {ka.correct_answers}/{ka.total_questions} correct
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Next Steps */}
      <Card>
        <CardHeader>
          <CardTitle>Recommended Next Steps</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="space-y-2">
            {results.next_steps.map((step, index) => (
              <li key={index} className="flex items-start gap-2">
                <span className="text-blue-600 font-semibold">{index + 1}.</span>
                <span>{step}</span>
              </li>
            ))}
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
```

---

## 🔗 React Query Hooks

### Custom Hooks
**Location:** `hooks/useDashboard.ts`

```tsx
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { DashboardData } from '@/types/api';

export function useDashboard() {
  return useQuery<DashboardData>({
    queryKey: ['dashboard'],
    queryFn: async () => {
      const response = await apiClient.get('/dashboard');
      return response.data;
    },
  });
}
```

**Location:** `hooks/useRecommendations.ts`

```tsx
import { useQuery } from '@tanstack/react-query';
import apiClient from '@/lib/api-client';
import { ContentRecommendationResponse } from '@/types/api';

export function useRecommendations(strategy: string = 'adaptive') {
  return useQuery<ContentRecommendationResponse>({
    queryKey: ['recommendations', strategy],
    queryFn: async () => {
      const response = await apiClient.get('/content/recommendations', {
        params: { strategy, limit: 10 }
      });
      return response.data;
    },
  });
}
```

---

**Ready to build! Start with authentication, then dashboard, then practice sessions.**
