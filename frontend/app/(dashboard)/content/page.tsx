'use client';

import { useState, useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { ContentCard } from '@/components/content/ContentCard';
import {
  BookOpen,
  Brain,
  TrendingDown,
  Target,
  Search,
  AlertCircle,
  Sparkles
} from 'lucide-react';
import type { ContentChunk, KnowledgeArea } from '@/types/api';

const recommendationStrategies = [
  {
    strategy: 'adaptive',
    name: 'Adaptive Learning',
    description: 'Content tailored to your weakest areas',
    icon: Brain,
    color: 'blue',
  },
  {
    strategy: 'recent_mistakes',
    name: 'Recent Mistakes',
    description: 'Based on questions you answered incorrectly',
    icon: TrendingDown,
    color: 'orange',
  },
  {
    strategy: 'ka_specific',
    name: 'Knowledge Area Focus',
    description: 'Deep dive into a specific knowledge area',
    icon: Target,
    color: 'purple',
  },
];

export default function ContentPage() {
  const [strategy, setStrategy] = useState('adaptive');
  const [selectedKA, setSelectedKA] = useState<string>('');
  const [knowledgeAreas, setKnowledgeAreas] = useState<KnowledgeArea[]>([]);
  const [content, setContent] = useState<ContentChunk[]>([]);
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

  useEffect(() => {
    fetchRecommendations();
  }, [strategy, selectedKA]);

  const fetchRecommendations = async () => {
    setLoading(true);
    setError('');

    try {
      const params: any = {
        strategy,
        limit: 10,
      };

      if (selectedKA && strategy === 'ka_specific') {
        params.ka_id = selectedKA;
      }

      const response = await apiClient.get('/v1/content/recommendations', { params });
      setContent(response.data.recommendations);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load recommendations');
    } finally {
      setLoading(false);
    }
  };

  const handleMarkAsRead = async (chunkId: string) => {
    try {
      await apiClient.post('/v1/content/mark-read', {
        chunk_id: chunkId,
      });
    } catch (err: any) {
      console.error('Failed to mark as read:', err);
    }
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Study Materials</h1>
        <p className="mt-1 text-gray-600">
          Personalized content recommendations to enhance your learning
        </p>
      </div>

      {/* Strategy Selection */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-blue-600" />
            Recommendation Strategy
          </CardTitle>
          <CardDescription>
            Choose how we recommend content for you
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-3">
            {recommendationStrategies.map((strat) => {
              const Icon = strat.icon;
              const isSelected = strategy === strat.strategy;

              return (
                <button
                  key={strat.strategy}
                  onClick={() => {
                    setStrategy(strat.strategy);
                    if (strat.strategy !== 'ka_specific') {
                      setSelectedKA('');
                    }
                  }}
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
                          ? `bg-${strat.color}-600`
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
                      <h3 className="font-semibold text-gray-900">{strat.name}</h3>
                      <p className="mt-1 text-sm text-gray-600">{strat.description}</p>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Knowledge Area Selection (for ka_specific strategy) */}
          {strategy === 'ka_specific' && (
            <div>
              <Label htmlFor="ka-select">Select Knowledge Area</Label>
              <select
                id="ka-select"
                value={selectedKA}
                onChange={(e) => setSelectedKA(e.target.value)}
                className="mt-2 w-full rounded-lg border border-gray-300 px-3 py-2 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              >
                <option value="">Choose a knowledge area...</option>
                {knowledgeAreas.map((ka) => (
                  <option key={ka.ka_id} value={ka.ka_id}>
                    {ka.ka_name} ({ka.weight_percentage}% of exam)
                  </option>
                ))}
              </select>
            </div>
          )}

          <Button
            onClick={fetchRecommendations}
            disabled={loading || (strategy === 'ka_specific' && !selectedKA)}
            className="w-full"
          >
            {loading ? 'Loading...' : 'Get Recommendations'}
          </Button>
        </CardContent>
      </Card>

      {/* Error Message */}
      {error && (
        <div className="flex items-center gap-2 rounded-lg bg-red-50 p-4 text-red-600">
          <AlertCircle className="h-5 w-5" />
          <p className="font-medium">{error}</p>
        </div>
      )}

      {/* Loading State */}
      {loading && (
        <div className="flex items-center justify-center h-64">
          <div className="text-center">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent mx-auto mb-4"></div>
            <p className="text-gray-600">Finding the best content for you...</p>
          </div>
        </div>
      )}

      {/* Content List */}
      {!loading && content.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">
              Recommended for You
            </h2>
            <span className="text-sm text-gray-500">
              {content.length} {content.length === 1 ? 'item' : 'items'}
            </span>
          </div>

          <div className="space-y-4">
            {content.map((chunk) => (
              <ContentCard
                key={chunk.chunk_id}
                content={chunk}
                onMarkAsRead={handleMarkAsRead}
              />
            ))}
          </div>
        </div>
      )}

      {/* Empty State */}
      {!loading && content.length === 0 && !error && (
        <Card className="border-dashed">
          <CardContent className="pt-6">
            <div className="text-center py-12">
              <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-semibold text-gray-900 mb-2">
                No content available
              </h3>
              <p className="text-gray-600 mb-4">
                {strategy === 'ka_specific' && !selectedKA
                  ? 'Please select a knowledge area to see recommendations'
                  : 'Try adjusting your recommendation strategy or complete some practice questions first'}
              </p>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
