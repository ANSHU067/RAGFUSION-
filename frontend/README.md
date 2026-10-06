# RAGFUSION Frontend

A production-ready React frontend for RAGFUSION - a trusted AI workspace for documents, websites, videos, and the answers inside them.

## Tech Stack

- **React 19** with JSX
- **Vite 8** for fast development and optimized builds
- **React Router DOM 7** for routing with lazy loading
- **Tailwind CSS 4** for styling
- **shadcn/ui** components (via Radix UI primitives)
- **Axios** for API communication with interceptors
- **React Hook Form + Zod** for form validation
- **Framer Motion** for animations
- **Lucide React** for icons
- **Sonner** for toast notifications
- **React Markdown** with syntax highlighting

## Project Structure

```
frontend/
├── public/
├── src/
│   ├── assets/           # Static assets
│   ├── components/
│   │   ├── chat/         # Chat components (window, bubbles, input, markdown)
│   │   ├── dashboard/    # Dashboard widgets (stats, workspaces, chats, etc.)
│   │   ├── forms/        # Form inputs (URL inputs for website/youtube)
│   │   ├── history/      # History components
│   │   ├── layout/       # Layout components (Sidebar, Navbar, DashboardLayout)
│   │   ├── readers/      # Reader components (previews, metadata, status)
│   │   ├── settings/     # Settings components
│   │   ├── upload/       # Upload components (cards, lists, progress, history)
│   │   ├── ui/           # shadcn/ui primitives
│   │   └── common/       # Shared components (hero, landing sections)
│   ├── context/          # React Context providers (Auth, User, Theme, Chat, Upload, Settings)
│   ├── hooks/            # Custom React hooks
│   ├── layouts/          # Page layouts (GlobalLayout)
│   ├── pages/
│   │   ├── auth/         # Login, Signup, Password reset
│   │   ├── dashboard/    # Dashboard, Workspaces, Chats, Search, Analytics, Team
│   │   ├── history/      # Session history
│   │   ├── profile/      # User profile
│   │   ├── settings/     # Application settings
│   │   ├── readers/      # Document, Website, YouTube, Chat readers
│   │   └── errors/       # 404, Error boundary
│   ├── routes/           # Router configuration
│   ├── services/         # API services (axios instance, feature APIs)
│   ├── store/            # State management (future: Zustand/Redux)
│   ├── constants/        # Application constants
│   ├── lib/              # Utilities (cn, validations)
│   ├── styles/           # Global styles
│   ├── types/            # TypeScript types (future)
│   ├── utils/            # Utility functions
│   ├── App.jsx           # Root component with ErrorBoundary
│   └── main.jsx          # Entry point
├── .env                  # Environment variables (create from .env.example)
├── .env.example          # Example environment variables
├── DOCUMENTATION.md      # Detailed documentation
├── package.json
└── README.md
```

## Getting Started

### Prerequisites

- Node.js 18+
- npm or pnpm

### Installation

```bash
cd frontend
npm install
```

### Development

```bash
npm run dev
```

The app will be available at `http://localhost:5173`

### Building for Production

```bash
npm run build
```

Output will be in `dist/`

### Linting & Type Checking

```bash
npm run lint
npm run typecheck
```

## Environment Variables

Copy `.env.example` to `.env` and configure:

```env
VITE_API_BASE_URL=http://localhost:8000
```

- `VITE_API_BASE_URL` - Backend API base URL. When unset, mock services are used for offline development.

## Features

### Authentication
- Login/Signup with email/password
- JWT token management with automatic refresh
- Protected routes with route guards
- Remember me functionality

### Dashboard
- Responsive sidebar navigation (collapsible, mobile drawer)
- Statistics cards with key metrics
- Quick actions for common tasks
- Recent chats and workspaces
- Theme switcher (light/dark/system)

### Chat Workspace
- Real-time message streaming simulation
- Markdown rendering with syntax highlighting
- Code blocks with copy/expand functionality
- Citations with source links
- Token counting
- Message actions (regenerate, copy, feedback, flag)
- File attachments

### Document Reader
- Drag-and-drop file upload with validation
- Progress tracking for upload and processing
- Document list with status badges
- Document preview modal
- Processing status and history

### Website Reader
- URL input with client-side validation
- Duplicate prevention
- Website preview cards
- Processing status with progress
- Metadata display

### YouTube Reader
- YouTube URL input (supports multiple formats)
- Video preview with embedded player
- Transcript and summary panels
- Processing status with progress
- Metadata display

### History
- Searchable, filterable session history
- Pagination with configurable page size
- Inline rename with validation
- Delete confirmation dialog
- Recent sessions sidebar

### Profile & Settings
- Editable profile with avatar upload
- Theme preferences (light/dark/system)
- Language selection
- Notification preferences (email/push/in-app)
- API configuration (base URL, key)
- Security settings (2FA, login alerts, sessions)

## Architecture

### State Management
Six React Context providers manage global state:
- **AuthContext** - Authentication, tokens, user
- **UserContext** - Profile data
- **ThemeContext** - Theme preference and resolved theme
- **ChatContext** - Current chat, history, messages
- **UploadContext** - File uploads, progress
- **SettingsContext** - User preferences

Provider hierarchy (outer to inner):
```
ThemeProvider
  SettingsProvider
    AuthProvider
      UserProvider
        ChatProvider
          UploadProvider
            App
```

### API Layer
- Centralized Axios instance with request/response interceptors
- Automatic Bearer token injection
- Transparent token refresh using refresh token
- Mock-first strategy: when `VITE_API_BASE_URL` is unset, in-memory mock data is used
- Feature-specific API modules: auth, chat, documents, website, youtube, history, settings

### Routing
- Route-level code splitting with lazy imports
- Protected dashboard routes
- Error boundary with fallback UI
- 404 page for unmatched routes

## Accessibility

- Semantic HTML with proper heading hierarchy
- ARIA labels, roles, and live regions
- Focus management with visible focus rings
- Skip links for keyboard navigation
- Reduced motion support (`prefers-reduced-motion`)
- High contrast mode support (`prefers-contrast: high`)
- Screen reader announcements for dynamic content

## Responsive Design

- Mobile-first approach
- Breakpoints: sm (640px), md (768px), lg (1024px), xl (1280px), 2xl (1536px)
- Fluid typography scaling
- Collapsible sidebar on desktop, drawer on mobile
- Touch-friendly targets (44px minimum)
- Adaptive layouts for all components

## Performance

- Code splitting by route and feature
- Lazy loading for all pages
- Three.js bundle separated into own chunk
- Memoization with React.memo, useMemo, useCallback
- Tree shaking enabled
- Optimized production builds

## Security

- No hardcoded API URLs or secrets
- Token storage in localStorage (consider httpOnly cookies for production)
- XSS-safe markdown rendering
- Input validation with Zod schemas
- Protected routes with authentication checks

## Backend Integration

The frontend is designed to integrate with a FastAPI backend. Set `VITE_API_BASE_URL` to connect.

Expected API endpoints:
- `POST /api/auth/login/` - Login
- `POST /api/auth/register/` - Register
- `POST /api/auth/refresh/` - Token refresh
- `GET /api/auth/me/` - Current user
- `GET/POST /chats` - Chat CRUD
- `POST /chats/{id}/messages` - Send message
- `GET/POST /documents` - Document CRUD
- `POST /documents/upload` - File upload
- `GET/POST /websites` - Website CRUD
- `GET/POST /youtube` - YouTube CRUD
- `GET /history` - Session history
- `GET/PATCH /settings` - Settings

## Scripts

| Command | Description |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm run lint` | Run ESLint |
| `npm run typecheck` | Run TypeScript type checking |

## License

MIT
