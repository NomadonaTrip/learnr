# LearnR Frontend - Next.js 14

AI-powered adaptive learning platform for CBAP exam preparation.

## 🚀 Quick Start

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.local.example .env.local

# Run development server
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

## 📋 Project Status

**Current Progress:** Foundation Complete ✅

### ✅ Completed
- Next.js 14 project structure with App Router
- TypeScript configuration
- Tailwind CSS + shadcn/ui setup
- API client with authentication interceptors
- Type definitions for all backend APIs
- Utility functions

### 🚧 To Build (Priority Order)

#### Week 2, Days 1-2: Authentication (6-8 hours)
1. **Auth Store & Hooks**
   - Create `lib/store/auth-store.ts` (Zustand)
   - Create `hooks/useAuth.ts`
   - Protected route wrapper

2. **Login Page** (`app/(auth)/login/page.tsx`)
   - Email/password form with validation
   - Error handling & loading states
   - Redirect to dashboard on success

3. **Register Page** (`app/(auth)/register/page.tsx`)
   - Registration form
   - Field validation
   - Auto-login after registration

#### Week 2, Days 3-4: Dashboard (8-10 hours)
4. **Dashboard Layout** (`app/(dashboard)/layout.tsx`)
   - Sidebar navigation
   - Header with user menu
   - Mobile responsive

5. **Dashboard Page** (`app/(dashboard)/dashboard/page.tsx`)
   - Overall progress card
   - KA progress bars
   - Exam readiness indicator
   - Quick action buttons
   - Recent activity list

#### Week 2, Days 5-7: Practice Sessions (10-12 hours)
6. **Practice Setup** (`app/(dashboard)/practice/page.tsx`)
   - Mode selection (adaptive/KA-specific)
   - Question count selector
   - Start session button

7. **Question Interface** (`app/(dashboard)/practice/[sessionId]/page.tsx`)
   - Question display
   - Answer choices (A/B/C/D)
   - Submit button
   - Progress indicator
   - Timer

8. **Answer Feedback Component**
   - Correct/incorrect indication
   - Explanation panel
   - Next question button

9. **Session Summary**
   - Score display
   - Time taken
   - KA breakdown
   - Review mistakes option

#### Week 3, Days 1-2: Content Recommendations (6-8 hours)
10. **Recommendations Page** (`app/(dashboard)/recommendations/page.tsx`)
    - Strategy selector (adaptive/recent mistakes/by KA)
    - Content cards grid
    - Filter & sort options

11. **Content Reader Modal**
    - Full content display
    - Mark as read
    - Helpful/not helpful feedback

#### Week 3, Days 3-5: Mock Exams (10-12 hours)
12. **Mock Exam Start** (`app/(dashboard)/mock-exam/page.tsx`)
    - Exam overview
    - KA distribution display
    - Instructions
    - Begin button

13. **Exam Interface** (`app/(dashboard)/mock-exam/[sessionId]/page.tsx`)
    - Question navigator (grid)
    - Timer countdown
    - Full-screen mode
    - Submit confirmation

14. **Results Page** (`app/(dashboard)/mock-exam/[sessionId]/results/page.tsx`)
    - Overall score (large display)
    - Pass/fail status
    - KA performance charts
    - Recommendations
    - Review answers option

#### Week 3, Days 6-7: Polish (8-10 hours)
15. **Mobile Optimization**
    - Responsive breakpoints
    - Touch-friendly buttons
    - Collapsible navigation

16. **UX Enhancements**
    - Loading skeletons
    - Toast notifications
    - Error boundaries
    - Empty states

## 🏗️ Project Structure

```
frontend/
├── app/
│   ├── (auth)/              # Authentication routes (no sidebar)
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/         # Protected routes (with sidebar)
│   │   ├── dashboard/
│   │   ├── practice/
│   │   ├── mock-exam/
│   │   ├── recommendations/
│   │   └── profile/
│   ├── layout.tsx           # Root layout
│   ├── globals.css          # Global styles
│   └── page.tsx             # Home/landing page
├── components/
│   ├── ui/                  # shadcn components
│   ├── auth/                # Auth-specific components
│   ├── dashboard/           # Dashboard components
│   ├── practice/            # Practice session components
│   └── shared/              # Shared components (Header, Sidebar)
├── hooks/
│   ├── useAuth.ts           # Authentication hook
│   ├── useQuestions.ts      # Questions fetching
│   └── useRecommendations.ts
├── lib/
│   ├── api-client.ts        # Axios instance ✅
│   ├── utils.ts             # Utility functions ✅
│   └── store/
│       └── auth-store.ts    # Zustand auth store
└── types/
    └── api.ts               # API type definitions ✅
```

## 🎨 shadcn/ui Components Needed

Install these as you build:

```bash
# Core components
npx shadcn-ui@latest add button card input label form
npx shadcn-ui@latest add badge progress tabs select
npx shadcn-ui@latest add dialog sheet toast
npx shadcn-ui@latest add radio-group separator
npx shadcn-ui@latest add skeleton avatar dropdown-menu
```

## 📡 API Integration

### Authentication

```typescript
import apiClient from '@/lib/api-client';

// Login
const response = await apiClient.post('/auth/login', {
  email: 'user@example.com',
  password: 'password123'
});

// Store tokens
localStorage.setItem('access_token', response.data.access_token);
localStorage.setItem('refresh_token', response.data.refresh_token);

// Get current user
const user = await apiClient.get('/auth/me');
```

### Dashboard Data

```typescript
const dashboard = await apiClient.get('/dashboard');
// Returns: DashboardData with competencies, sessions, etc.
```

### Practice Sessions

```typescript
// Start session
const session = await apiClient.post('/sessions', {
  session_type: 'practice',
  mode: 'adaptive'
});

// Get next question
const question = await apiClient.get(`/sessions/${sessionId}/next-question`);

// Submit answer
const feedback = await apiClient.post(`/sessions/${sessionId}/attempt`, {
  selected_choice_id: choiceId
});
```

### Content Recommendations

```typescript
const recs = await apiClient.get('/content/recommendations', {
  params: {
    strategy: 'adaptive',
    limit: 5
  }
});
```

### Mock Exams

```typescript
// Create mock exam
const exam = await apiClient.post('/exams/mock');

// Get results
const results = await apiClient.get(`/exams/${sessionId}/results`);
```

## 🎯 Development Tips

### 1. Use React Query for Data Fetching

```typescript
import { useQuery } from '@tanstack/react-query';

function useDashboard() {
  return useQuery({
    queryKey: ['dashboard'],
    queryFn: () => apiClient.get('/dashboard').then(res => res.data)
  });
}
```

### 2. Form Handling with React Hook Form + Zod

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email(),
  password: z.string().min(8)
});

const form = useForm({
  resolver: zodResolver(loginSchema)
});
```

### 3. Protected Routes

```typescript
// middleware.ts
export function middleware(request: NextRequest) {
  const token = request.cookies.get('access_token');
  if (!token && request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.redirect(new URL('/login', request.url));
  }
}
```

## 🎨 Design Guidelines

- **Primary Color:** Blue (#3B82F6)
- **Success:** Green (#10B981)
- **Warning:** Yellow (#F59E0B)
- **Danger:** Red (#EF4444)
- **Font:** Inter (system default)
- **Spacing:** Consistent 4px grid

### Component Examples

**Dashboard Card:**
```tsx
<Card>
  <CardHeader>
    <CardTitle>Overall Progress</CardTitle>
  </CardHeader>
  <CardContent>
    <div className="text-4xl font-bold">75.5%</div>
    <Progress value={75.5} className="mt-2" />
  </CardContent>
</Card>
```

**KA Progress Bar:**
```tsx
<div className="space-y-2">
  <div className="flex justify-between text-sm">
    <span>Business Analysis Planning</span>
    <span className="font-semibold">68.5%</span>
  </div>
  <Progress value={68.5} className="h-2" />
</div>
```

## 🧪 Testing

```bash
# Run tests (when added)
npm run test

# Type check
npm run type-check

# Lint
npm run lint
```

## 🚀 Deployment

### Vercel (Recommended)

```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel
```

### Environment Variables (Production)

```bash
NEXT_PUBLIC_API_URL=https://api.learnr.com
NEXT_PUBLIC_APP_NAME=LearnR
NEXT_PUBLIC_APP_URL=https://learnr.com
```

## 📊 Performance Targets

- **First Contentful Paint:** < 1.5s
- **Time to Interactive:** < 3.5s
- **Lighthouse Score:** > 90

## 🔗 Useful Links

- [Next.js 14 Docs](https://nextjs.org/docs)
- [shadcn/ui Components](https://ui.shadcn.com)
- [TanStack Query](https://tanstack.com/query/latest)
- [Tailwind CSS](https://tailwindcss.com)
- [Backend API Docs](http://localhost:8000/docs)

## 📝 Notes

- Backend runs on `http://localhost:8000`
- Frontend runs on `http://localhost:3000`
- All API endpoints prefixed with `/v1`
- Tokens stored in localStorage
- Auto-refresh on 401 errors

---

**Built with ❤️ for CBAP learners**
