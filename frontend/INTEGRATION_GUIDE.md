# Frontend Integration Guide

## Overview

This frontend combines the best of both worlds:
- **Modern architecture** from the NextJS frontend (state management, hooks, patterns)
- **EDA-specific functionality** from the old Vite frontend (job processing, SSE streaming)

## What Was Integrated

### From NextJS Frontend (`wireframe/frontend_nextjs_backup/`)

✅ **Types** (`src/types/`)
- `api.ts` - Generic API response types
- `auth.ts` - User and authentication types
- `chat.ts` - Chat message types
- `conversation.ts` - Conversation types
- `index.ts` - Barrel export

✅ **Stores** (`src/stores/`) - Zustand state management
- `auth-store.ts` - Authentication state
- `chat-store.ts` - Chat conversations
- `conversation-store.ts` - Conversation management
- `local-chat-store.ts` - Local chat state
- `theme-store.ts` - Theme switching
- `sidebar-store.ts` - UI state
- `chat-sidebar-store.ts` - Chat sidebar state

✅ **Lib** (`src/lib/`)
- `api-client.ts` - Clean REST API client with error handling
- `constants.ts` - App constants, routes, API endpoints
- `utils.ts` - Utility functions (cn, etc.)

✅ **Hooks** (`src/hooks/`)
- `use-auth.ts` - Authentication hook
- `use-chat.ts` - Chat functionality
- `use-conversations.ts` - Conversation management
- `use-local-chat.ts` - Local chat
- `use-websocket.ts` - WebSocket connections
- `use-mobile.tsx` - Mobile detection
- `use-toast.ts` - Toast notifications

### From Old Vite Frontend

✅ **EDA API** (`src/lib/api-eda.ts`) - **Your Core Functionality**
- `analyzeDatasheet()` - File upload for datasheet analysis
- `getJobStatus()` - Poll job status
- `streamJobStatus()` - **Server-Sent Events for real-time updates**
- `resumeJob()` - **Human-in-the-loop: resume with missing variables**
- `downloadSchematic()` - Download KiCad schematic
- `downloadBOM()` - Download bill of materials

### Adaptations for Vite

✅ Removed all `"use client"` directives (Next.js specific)
✅ Changed `process.env.NEXT_PUBLIC_*` to `import.meta.env.VITE_*`
✅ Updated API routes to work with Vite proxy
✅ Added `zustand` dependency to package.json

## Architecture

```
src/
├── types/           # TypeScript type definitions
├── stores/          # Zustand state management stores
├── lib/
│   ├── api-client.ts    # Generic REST API client
│   ├── api-eda.ts       # EDA-specific API (jobs, datasheet, SSE)
│   ├── constants.ts     # App constants & routes
│   └── utils.ts         # Utility functions
├── hooks/           # Custom React hooks
├── components/      # React components
└── pages/           # Application pages
```

## How to Use

### 1. Install Dependencies

```bash
cd wireframe/frontend
npm install
```

### 2. EDA Workflows (Your Main Use Case)

```typescript
import { analyzeDatasheet, streamJobStatus, resumeJob } from '@/lib/api-eda';

// Upload and analyze datasheet
const handleAnalyze = async (file: File) => {
  const response = await analyzeDatasheet(file, {
    V_in: 12.0,
    V_out: 5.0,
  });

  // Stream real-time updates (human-in-the-loop)
  const eventSource = streamJobStatus(response.job_id, (event) => {
    console.log('Job update:', event);

    if (event.data.status === 'awaiting_input') {
      // Pause for user input
      setNeedUserInput(true);
    }
  });

  // Later: resume with missing variables
  await resumeJob(response.job_id, {
    I_out_max: 2.5,
  });
};
```

### 3. Authentication (Supporting Feature)

```typescript
import { useAuthStore } from '@/stores';

function LoginPage() {
  const { user, isAuthenticated, checkAuth } = useAuthStore();

  useEffect(() => {
    checkAuth();
  }, []);

  return <div>{user?.email}</div>;
}
```

### 4. Chat (Supporting Feature)

```typescript
import { useChatStore } from '@/stores';
import { useWebSocket } from '@/hooks';

function ChatComponent() {
  const { messages, addMessage } = useChatStore();
  const { sendMessage, isConnected } = useWebSocket();

  // Use for asking questions about designs, etc.
}
```

### 5. Theme Switching

```typescript
import { useThemeStore } from '@/stores';

function ThemeToggle() {
  const { theme, setTheme } = useThemeStore();

  return (
    <button onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
      Toggle Theme
    </button>
  );
}
```

## Key Patterns

### API Client Pattern

```typescript
import { apiClient } from '@/lib/api-client';

// GET request
const user = await apiClient.get<User>('/users/me');

// POST request
const result = await apiClient.post('/jobs', { name: 'My Design' });

// Error handling
try {
  await apiClient.get('/protected');
} catch (error) {
  if (error instanceof ApiError) {
    console.error(error.status, error.message);
  }
}
```

### Store Pattern (Zustand)

```typescript
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface MyState {
  count: number;
  increment: () => void;
}

export const useMyStore = create<MyState>()(
  persist(
    (set) => ({
      count: 0,
      increment: () => set((state) => ({ count: state.count + 1 })),
    }),
    { name: 'my-storage' }
  )
);
```

## Environment Variables

Update `wireframe/frontend/.env`:

```bash
# Backend API Configuration
VITE_API_URL=http://localhost:8080
VITE_WS_URL=ws://localhost:8080

# Optional: Keep Supabase if needed
VITE_SUPABASE_PROJECT_ID=...
VITE_SUPABASE_PUBLISHABLE_KEY=...
VITE_SUPABASE_URL=...
```

## Running the Application

**Development:**
```bash
cd wireframe/frontend
npm run dev
# Frontend runs on http://localhost:3000
# API calls proxied to http://localhost:8080
```

**Docker:**
```bash
cd wireframe
make wireframe
# Backend: http://localhost:8080
# Frontend: http://localhost:3000
```

## Next Steps

1. **Build your EDA editor UI** using the components from `src/components/`
2. **Integrate job status streaming** for real-time feedback during design generation
3. **Use chat as a side feature** for asking design questions
4. **Add authentication** if you need user accounts
5. **Customize theme** with the theme store

## File Locations

- **Backup of NextJS frontend:** `wireframe/frontend_nextjs_backup/`
- **Backup of old EDA API:** `wireframe/frontend/src/lib/api-eda-legacy.ts`
- **Current integrated frontend:** `wireframe/frontend/`

## Notes

- The old Vite frontend (`frontend/` in root) remains unchanged
- All modern patterns are now in `wireframe/frontend/`
- SSE streaming is your key feature for human-in-the-loop workflows
- Chat/conversations are available but optional for your use case
