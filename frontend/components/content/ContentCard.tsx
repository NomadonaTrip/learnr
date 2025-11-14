'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { BookOpen, ExternalLink, CheckCircle2 } from 'lucide-react';
import { useState } from 'react';
import type { ContentChunk } from '@/types/api';

interface ContentCardProps {
  content: ContentChunk;
  onMarkAsRead?: (chunkId: string) => void;
}

export function ContentCard({ content, onMarkAsRead }: ContentCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isRead, setIsRead] = useState(false);

  const handleMarkAsRead = () => {
    setIsRead(true);
    if (onMarkAsRead) {
      onMarkAsRead(content.chunk_id);
    }
  };

  const contentPreview = content.content_text.slice(0, 200);
  const showReadMore = content.content_text.length > 200;

  return (
    <Card className={`transition-all ${isRead ? 'opacity-75 border-green-200' : ''}`}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <div className="flex items-center gap-2 mb-2">
              <BookOpen className="h-4 w-4 text-blue-600" />
              <span className="text-sm font-medium text-blue-600">
                {content.ka_name}
              </span>
              {content.domain_name && (
                <>
                  <span className="text-gray-400">•</span>
                  <span className="text-sm text-gray-600">{content.domain_name}</span>
                </>
              )}
            </div>
            <CardTitle className="text-lg">{content.title}</CardTitle>
            {isRead && (
              <div className="flex items-center gap-1 mt-2 text-green-600">
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-xs font-medium">Read</span>
              </div>
            )}
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="prose prose-sm max-w-none">
          <p className="text-gray-700 leading-relaxed">
            {isExpanded ? content.content_text : contentPreview}
            {!isExpanded && showReadMore && '...'}
          </p>
        </div>

        <div className="flex items-center gap-2 pt-2 border-t border-gray-100">
          {showReadMore && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setIsExpanded(!isExpanded)}
            >
              {isExpanded ? 'Show Less' : 'Read More'}
            </Button>
          )}

          {content.source_url && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => window.open(content.source_url, '_blank')}
            >
              <ExternalLink className="h-3 w-3 mr-1" />
              Source
            </Button>
          )}

          {!isRead && (
            <Button
              size="sm"
              onClick={handleMarkAsRead}
              className="ml-auto"
            >
              Mark as Read
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
