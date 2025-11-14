'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  GraduationCap,
  LayoutDashboard,
  BookOpen,
  Brain,
  ClipboardCheck,
  TrendingUp,
  Calendar
} from 'lucide-react';

const navigationItems = [
  {
    name: 'Dashboard',
    href: '/dashboard',
    icon: LayoutDashboard,
  },
  {
    name: 'Practice',
    href: '/practice',
    icon: Brain,
  },
  {
    name: 'Mock Exams',
    href: '/exams',
    icon: ClipboardCheck,
  },
  {
    name: 'Study Materials',
    href: '/content',
    icon: BookOpen,
  },
  {
    name: 'Review Cards',
    href: '/reviews',
    icon: Calendar,
  },
  {
    name: 'Progress',
    href: '/progress',
    icon: TrendingUp,
  },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex h-full flex-col bg-white border-r border-gray-200">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-gray-200 px-6">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
          <GraduationCap className="h-6 w-6 text-white" />
        </div>
        <span className="text-xl font-bold text-gray-900">LearnR</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navigationItems.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors
                ${
                  isActive
                    ? 'bg-blue-50 text-blue-600'
                    : 'text-gray-700 hover:bg-gray-50 hover:text-gray-900'
                }
              `}
            >
              <Icon className="h-5 w-5" />
              {item.name}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-gray-200 p-4">
        <div className="rounded-lg bg-blue-50 p-3">
          <p className="text-xs font-medium text-blue-900">CBAP Certification</p>
          <p className="mt-1 text-xs text-blue-700">Master 6 Knowledge Areas</p>
        </div>
      </div>
    </div>
  );
}
