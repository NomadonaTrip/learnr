'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Brain, TrendingUp, Target, Zap, AlertCircle } from 'lucide-react';
import type { KnowledgeArea } from '@/types/api';

const sessionTypes = [
  {
    type: 'diagnostic',
    name: 'Diagnostic Test',
    description: 'Assess your current knowledge level across all areas',
    icon: Target,
    color: 'blue',
  },
  {
    type: 'practice',
    name: 'Adaptive Practice',
    description: 'Practice questions tailored to your skill level',
    icon: Brain,
    color: 'purple',
  },
  {
    type: 'weak_areas',
    name: 'Focus on Weak Areas',
    description: 'Target your weakest knowledge areas for improvement',
    icon: TrendingUp,
    color: 'orange',
  },
  {
    type: 'quick_review',
    name: 'Quick Review',
    description: 'Short 10-question session for daily practice',
    icon: Zap,
    color: 'green',
  },
];

export default function PracticePage() {
  const router = useRouter();
  const [selectedType, setSelectedType] = useState('practice');
  const [selectedKA, setSelectedKA] = useState<string>('');
  const [knowledgeAreas, setKnowledgeAreas] = useState<KnowledgeArea[]>([]);
  const [questionCount, setQuestionCount] = useState(20);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchKnowledgeAreas() {
      try {
        const response = await apiClient.get('/v1/courses/current/knowledge-areas');
        setKnowledgeAreas(response.data);
      } catch (err: any) {
        console.error('Failed to load knowledge areas:', err);
      }
    }

    fetchKnowledgeAreas();
  }, []);

  const handleStartSession = async () => {
    setLoading(true);
    setError('');

    try {
      const response = await apiClient.post('/v1/sessions', {
        session_type: selectedType,
        ka_id: selectedKA || null,
        target_question_count: questionCount,
      });

      router.push(`/practice/${response.data.session_id}`);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start session');
      setLoading(false);
    }
  };

  const selectedSessionType = sessionTypes.find((t) => t.type === selectedType);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Practice Questions</h1>
        <p className="mt-1 text-gray-600">
          Choose a practice session type to improve your CBAP knowledge
        </p>
      </div>

      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Session Type Selection */}
      <div>
        <Label className="text-base font-semibold">Select Session Type</Label>
        <div className="mt-3 grid gap-4 md:grid-cols-2">
          {sessionTypes.map((type) => {
            const Icon = type.icon;
            const isSelected = selectedType === type.type;

            return (
              <button
                key={type.type}
                onClick={() => setSelectedType(type.type)}
                className={`text-left p-4 rounded-lg border-2 transition-all ${
                  isSelected
                    ? 'border-blue-500 bg-blue-50'
                    : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-start gap-3">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-lg ${
                      isSelected
                        ? `bg-${type.color}-600`
                        : 'bg-gray-200'
                    }`}
                  >
                    <Icon
                      className={`h-5 w-5 ${
                        isSelected ? 'text-white' : 'text-gray-600'
                      }`}
                    />
                  </div>
                  <div className="flex-1">
                    <h3 className="font-semibold text-gray-900">{type.name}</h3>
                    <p className="mt-1 text-sm text-gray-600">{type.description}</p>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Session Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Session Settings</CardTitle>
          <CardDescription>Customize your practice session</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Knowledge Area Selection */}
          <div>
            <Label htmlFor="ka-select">
              Knowledge Area (Optional)
            </Label>
            <select
              id="ka-select"
              value={selectedKA}
              onChange={(e) => setSelectedKA(e.target.value)}
              className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              <option value="">All Knowledge Areas</option>
              {knowledgeAreas.map((ka) => (
                <option key={ka.ka_id} value={ka.ka_id}>
                  {ka.ka_name} ({ka.weight_percentage}% of exam)
                </option>
              ))}
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Leave blank to practice all areas based on your competency
            </p>
          </div>

          {/* Question Count */}
          <div>
            <Label htmlFor="question-count">
              Number of Questions: {questionCount}
            </Label>
            <input
              type="range"
              id="question-count"
              min="5"
              max="50"
              step="5"
              value={questionCount}
              onChange={(e) => setQuestionCount(parseInt(e.target.value))}
              className="mt-2 w-full"
            />
            <div className="mt-1 flex justify-between text-xs text-gray-500">
              <span>5 questions</span>
              <span>50 questions</span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Start Button */}
      <Card className="border-blue-200 bg-blue-50">
        <CardContent className="pt-6">
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-semibold text-blue-900">Ready to start?</h3>
              <p className="mt-1 text-sm text-blue-700">
                {selectedSessionType?.name} • {questionCount} questions
                {selectedKA && ` • ${knowledgeAreas.find((ka) => ka.ka_id === selectedKA)?.ka_name}`}
              </p>
            </div>
            <Button
              onClick={handleStartSession}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700"
            >
              {loading ? 'Starting...' : 'Start Session'}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
