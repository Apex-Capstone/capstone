# APEX (AI Patient Experience Simulator) - Frontend

A modern React + TypeScript frontend for the APEX (AI Patient Experience Simulator) project, built with Vite, TailwindCSS, and React Router.

**✅ Aligned with SRS v0.1 (Oct 2025)** - This frontend implementation fully supports the Software Requirements Specification for the APEX (AI Patient Experience Simulator) project, including SPIKES framework integration, role-based access control, and comprehensive feedback systems.

## 🚀 Tech Stack

- **React 19** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool and dev server
- **TailwindCSS** - Utility-first CSS framework
- **shadcn/ui** - Component library
- **React Router DOM** - Client-side routing
- **Zustand** - State management (auth)
- **Axios** - HTTP client

## 📋 Prerequisites

- Node.js 18+ and npm
- FastAPI backend (optional for now - frontend uses mock data)

## 🔧 Installation

1. Install dependencies:
```bash
npm install
```

## ⚙️ Environment Setup

1. Copy the example environment file:
```bash
cp .env.example .env
```

2. Configure the API URL in `.env`:
```
VITE_API_URL=http://localhost:8000
```

**Note:** Currently, the frontend uses mock data. Update `VITE_API_URL` when the FastAPI backend is ready.

## 🏃 Development

Start the development server:
```bash
npm run dev
```

The app will be available at `http://localhost:5173` (or the next available port).

## 📁 Project Structure

```
src/
├── api/              # API client with mock functions
│   └── client.ts     # Axios instance and API functions
├── components/       # Reusable React components
│   ├── ui/          # shadcn/ui components
│   ├── CaseCard.tsx
│   ├── ChatBubble.tsx
│   ├── FeedbackChart.tsx
│   ├── MetricCard.tsx
│   ├── Navbar.tsx
│   ├── ProtectedRoute.tsx
│   └── Sidebar.tsx
├── pages/            # Page components
│   ├── Admin.tsx
│   ├── CaseDetail.tsx
│   ├── Dashboard.tsx
│   ├── Feedback.tsx
│   └── Login.tsx
├── store/            # Zustand stores
│   └── authStore.ts  # Authentication state
├── lib/              # Utility functions
│   └── utils.ts
└── main.tsx          # Application entry point
```

## 🛣️ Routes

- `/` - Redirects to `/dashboard` or `/login` based on auth
- `/login` - Login page (redirects to dashboard if authenticated)
- `/dashboard` - Main trainee dashboard with case list (protected)
- `/case/:caseId` - Chat interface for a specific case (protected)
- `/feedback/:sessionId` - Feedback summary view (protected)
- `/research` - Research analytics dashboard (protected, both roles)
- `/admin` - Admin portal dashboard (protected, admin role required)

## 📋 SRS v0.1 Requirements Mapping

This frontend implementation addresses all functional and non-functional requirements from the Software Requirements Specification:

### 🎯 Functional Requirements (FR)

| FR ID | Requirement | Implementation | Location |
|-------|-------------|---------------|----------|
| **FR-1** | Authentication & Role Handling | ✅ Role-based login with `trainee`/`admin` roles | `authStore.ts`, `ProtectedRoute.tsx` |
| **FR-2** | Case Selection | ✅ SPIKES-focused virtual patient cases with demographics | `Dashboard.tsx`, `CaseCard.tsx` |
| **FR-3** | Chat Interface | ✅ Text chat with patient emotion indicators | `CaseDetail.tsx`, `ChatBubble.tsx` |
| **FR-4** | Session Management | ✅ Real-time session timer and SPIKES stage tracking | `CaseDetail.tsx` |
| **FR-5** | Voice Input | ✅ Microphone capture uploads audio for backend transcription | `CaseDetail.tsx` |
| **FR-6** | Feedback Dashboard | ✅ SPIKES coverage radar chart and enhanced metrics | `Feedback.tsx`, `FeedbackChart.tsx` |
| **FR-7** | Admin Dashboard | ✅ Tabbed interface with user management and analytics | `Admin.tsx` |
| **FR-8** | Research API View | ✅ Read-only analytics with anonymized data | `Research.tsx` |
| **FR-10** | End Session | ✅ "End Session" button redirects to feedback | `CaseDetail.tsx` |
| **FR-12** | Enhanced Metrics | ✅ Empathy scores, open-question ratios, dialogue examples | `Feedback.tsx` |
| **FR-13** | User Overview | ✅ Admin can view trainee performance and statistics | `Admin.tsx` (Users tab) |
| **FR-14** | Session Logs | ✅ Admin can access session transcripts and data | `Admin.tsx` (Sessions tab) |
| **FR-15** | Fairness Metrics | ✅ Bias probe consistency and demographic parity | `Research.tsx` |

### 🛡️ Non-Functional Requirements (NFR)

| NFR ID | Requirement | Implementation | Status |
|--------|-------------|---------------|---------|
| **NFR 7.2** | UI/UX Performance | ✅ Skeleton loaders, responsive design | Dashboard, Feedback pages |
| **NFR 7.3** | Accessibility | ✅ WCAG-compliant color contrasts, semantic HTML | All components |
| **NFR 7.6** | Security | ✅ Role-based access control, protected routes | `ProtectedRoute.tsx` |

### 🎨 Key UI Features

- **SPIKES Framework Integration**: All case interactions are designed around the 6-stage SPIKES communication model
- **Real-time Session Tracking**: Live timer and stage progression indicators
- **Voice Input**: Browser microphone capture uploads audio to the backend and inserts the returned transcript into chat
- **Comprehensive Feedback**: Multi-dimensional scoring with dialogue examples
- **Admin Analytics**: Tabbed dashboard with user management, session logs, and performance analytics
- **Research Interface**: Privacy-focused analytics with fairness metrics
- **Responsive Design**: Mobile-first approach with Tailwind CSS
- **Skeleton Loading**: Enhanced UX with loading states for all async operations

### 💾 Mock Data Structure

The frontend includes comprehensive mock data that mirrors the expected backend API structure:

- **Virtual Patient Cases**: 5 SPIKES-focused scenarios with patient demographics and emotions
- **Enhanced Feedback**: SPIKES coverage metrics, conversation analysis, and dialogue examples
- **Admin Data**: User overviews, session logs, and analytics trends
- **Research Data**: Anonymized sessions with fairness metrics

All mock data includes realistic SPIKES framework examples and can be easily replaced with actual API calls when the FastAPI backend is ready.

## 🔐 Authentication

The app uses Zustand for auth state management with localStorage persistence.

**Demo Credentials:**
- Any email/password combination (defaults to trainee role)
- `admin@example.com` / `admin123` - Admin access

## 📡 API Integration

### Current Status
The frontend is wired for real API calls through `src/api/*.ts`. Audio input specifically uses the session upload endpoint and expects the backend to return a transcript plus the patient reply.

### Backend Integration (Future)
When the FastAPI backend is ready:

1. Update `VITE_API_URL` in `.env` to point to your backend
2. Replace mock implementations in `src/api/client.ts` with actual API calls
3. Uncomment the axios interceptor in `client.ts` to add auth tokens
4. The following endpoints are expected:

   - `POST /auth/login` - User login
   - `GET /cases` - Fetch all cases
   - `GET /cases/{case_id}` - Fetch case details with messages
   - `POST /sessions/{session_id}/audio` - Upload recorded voice input and receive transcript + patient reply
   - `GET /feedback/{session_id}` - Fetch feedback for a session
   - `GET /admin/stats` - Fetch admin statistics (admin only)

All endpoints are documented with TODO comments in `src/api/client.ts`.

## 🎨 Styling

- TailwindCSS for utility-first styling
- shadcn/ui components for consistent UI
- Responsive design (mobile-first)
- Light mode only (dark mode can be added later)

## 📦 Build

Build for production:
```bash
npm run build
```

Preview production build:
```bash
npm run preview
```

## 🧪 Linting

Run ESLint:
```bash
npm run lint
```

## 📝 Notes

- All routes are protected except `/login`
- Admin routes require the `admin` role
- Mock data is used until FastAPI backend integration
- Auth tokens are stored in localStorage via Zustand persist middleware

## 🤝 Contributing

This is a modular frontend scaffold designed to connect to a FastAPI backend. Focus areas:
- Clean component structure
- Type-safe API interfaces
- Reusable UI components
- Clear separation of concerns

---

## 🚀 Quick Start

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env to configure VITE_API_URL if needed
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```

4. **Login with demo credentials:**
   - Trainee: Any email/password combination
   - Admin: `admin@example.com` / `admin123`

## 🔄 Backend Integration

The frontend is designed to seamlessly integrate with the FastAPI backend:

1. **Update API URL:** Set `VITE_API_URL` in `.env` to your backend endpoint
2. **Enable Auth Interceptor:** Uncomment the auth token interceptor in `client.ts`
3. **Replace Mock Functions:** All API functions in `client.ts` are clearly marked with TODO comments

Expected backend endpoints:
- `POST /auth/login`
- `GET /cases`, `GET /cases/{id}`
- `GET /feedback/{session_id}`
- `GET /admin/stats`
- `GET /research/data`

---

**Status:** ✅ Frontend complete and SRS v0.1 compliant. Ready for FastAPI backend integration.
