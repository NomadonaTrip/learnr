'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Clock, AlertCircle } from 'lucide-react';

interface ExamTimerProps {
  durationMinutes: number;
  onTimeUp?: () => void;
}

export function ExamTimer({ durationMinutes, onTimeUp }: ExamTimerProps) {
  const [secondsRemaining, setSecondsRemaining] = useState(durationMinutes * 60);

  useEffect(() => {
    if (secondsRemaining <= 0) {
      if (onTimeUp) {
        onTimeUp();
      }
      return;
    }

    const timer = setInterval(() => {
      setSecondsRemaining((prev) => {
        if (prev <= 1) {
          clearInterval(timer);
          return 0;
        }
        return prev - 1;
      });
    }, 1000);

    return () => clearInterval(timer);
  }, [secondsRemaining, onTimeUp]);

  const hours = Math.floor(secondsRemaining / 3600);
  const minutes = Math.floor((secondsRemaining % 3600) / 60);
  const seconds = secondsRemaining % 60;

  const isLowTime = secondsRemaining < 300; // Less than 5 minutes
  const isCritical = secondsRemaining < 60; // Less than 1 minute

  return (
    <Card className={`${isCritical ? 'border-red-500 bg-red-50' : isLowTime ? 'border-yellow-500 bg-yellow-50' : ''}`}>
      <CardContent className="pt-6">
        <div className="flex items-center gap-3">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${
            isCritical ? 'bg-red-600' : isLowTime ? 'bg-yellow-600' : 'bg-blue-600'
          }`}>
            <Clock className="h-5 w-5 text-white" />
          </div>
          <div className="flex-1">
            <p className={`text-sm font-medium ${
              isCritical ? 'text-red-900' : isLowTime ? 'text-yellow-900' : 'text-gray-700'
            }`}>
              Time Remaining
            </p>
            <p className={`text-2xl font-bold ${
              isCritical ? 'text-red-900' : isLowTime ? 'text-yellow-900' : 'text-gray-900'
            }`}>
              {hours > 0 && `${hours}:`}
              {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
            </p>
          </div>
          {isLowTime && (
            <AlertCircle className={`h-5 w-5 ${isCritical ? 'text-red-600' : 'text-yellow-600'}`} />
          )}
        </div>
      </CardContent>
    </Card>
  );
}
