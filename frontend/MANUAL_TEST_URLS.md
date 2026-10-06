# RAGFUSION Frontend - Manual Test URLs

Generated after Phase 16 full recovery and route audit.

## Base URL
```
http://localhost:5173
```
(or whichever port Vite assigns, typically 5173 or 5174)

---

## Public Routes (GlobalLayout)

| Route | URL | Expected Behavior | Components Involved | Files Responsible |
|-------|-----|-------------------|---------------------|-------------------|
| Home | `http://localhost:5173/` | Landing page with hero, features, pricing, CTA | HeroScene, TechCloud, ProductPreview, FeaturesAndBento, WorkflowPipeline, ComparisonStats, UseCasesPricingFaq, FinalCta | `src/pages/HomePage.jsx`, `src/components/common/*`, `src/layouts/GlobalLayout.jsx` |
| Login | `http://localhost:5173/login` | Email/password form, remember me, forgot password link, signup link | LoginPage, Input, Button, Card, useForm (react-hook-form), zod validation | `src/pages/auth/LoginPage.jsx`, `src/lib/validations.js`, `src/components/ui/*` |
| Signup | `http://localhost:5173/signup` | Name, email, password, confirm password form, login link | SignupPage, Input, Button, Card, useForm, zod validation | `src/pages/auth/SignupPage.jsx`, `src/lib/validations.js` |
| Forgot Password | `http://localhost:5173/forgot-password` | Email input, sends reset link, success state, back to login | ForgotPasswordPage, Input, Button, Card, useForm | `src/pages/auth/ForgotPasswordPage.jsx` |
| Reset Password | `http://localhost:5173/reset-password?token=xxx` | Validates token, new password + confirm, redirects to login on success | ResetPasswordPage, Input, Button, Card, useForm, useSearchParams | `src/pages/auth/ResetPasswordPage.jsx` |

---

## Protected Dashboard Routes (DashboardLayout)

| Route | URL | Expected Behavior | Components Involved | Files Responsible |
|-------|-----|-------------------|---------------------|-------------------|
| Dashboard Home | `http://localhost:5173/dashboard` | Welcome header, statistics cards, quick actions, workspace cards, recent chats, sidebar quick links | DashboardPage, StatisticsCards, QuickActions, WorkspaceCards, RecentChats, ThemeSwitcher | `src/pages/dashboard/DashboardPage.jsx`, `src/components/dashboard/*` |
| Workspaces | `http://localhost:5173/dashboard/workspaces` | Grid/list view, search, create workspace, workspace cards with stats, dropdown actions | WorkspacesPage, Card, Button, Input, DropdownMenu, Badge, Avatar | `src/pages/dashboard/WorkspacesPage.jsx` |
| Chats | `http://localhost:5173/dashboard/chats` | List of chats with filters (all/pinned/recent), search, new chat button | ChatsPage, Card, Button, Input, DropdownMenu, Badge, Link | `src/pages/dashboard/ChatsPage.jsx` |
| Search | `http://localhost:5173/dashboard/search` | Global search bar, filters by type, results with scores, recent searches | SearchPage, Input, Button, Card, Badge | `src/pages/dashboard/SearchPage.jsx` |
| Notifications | `http://localhost:5173/dashboard/notifications` | Notification list with filters, mark all read, unread badges, categories | NotificationsPage, Notifications component, ScrollArea, DropdownMenu | `src/pages/dashboard/NotificationsPage.jsx`, `src/components/dashboard/Notifications.jsx` |
| Profile | `http://localhost:5173/dashboard/profile` | Avatar upload, name, email, role, organization, timezone, language, bio, save/cancel | ProfilePage, Avatar, Input, Label, Button, Card, useRef, localStorage | `src/pages/profile/ProfilePage.jsx` |
| Settings | `http://localhost:5173/dashboard/settings` | Appearance (light/dark/system), language, notifications, API config, account, security | SettingsPage, ThemeContext, Switch, Input, Select, Button, Card | `src/pages/settings/SettingsPage.jsx`, `src/context/ThemeContext.jsx` |
| Analytics | `http://localhost:5173/dashboard/analytics` | Statistics cards, placeholder charts for usage, cost, response times, tokens, errors | AnalyticsPage, StatisticsCards, Card | `src/pages/dashboard/AnalyticsPage.jsx` |
| History | `http://localhost:5173/dashboard/history` | Searchable/filterable table of sessions, pagination, recent sessions sidebar, edit/delete | HistoryPage, Card, Input, Select, Table, Badge, Button, DropdownMenu, historyApi | `src/pages/history/HistoryPage.jsx`, `src/services/historyApi.js` |
| Team | `http://localhost:5173/dashboard/team` | Member list with roles/status, dropdown actions, pending invitations, invite button | TeamPage, Card, Avatar, Badge, DropdownMenu, Button | `src/pages/dashboard/TeamPage.jsx` |

---

## Source Management Routes (DashboardLayout)

| Route | URL | Expected Behavior | Components Involved | Files Responsible |
|-------|-----|-------------------|---------------------|-------------------|
| Documents Index | `http://localhost:5173/documents` | Upload zone (drag & drop), file input, progress placeholder | SourcePage (documents config), Input, Button, Progress | `src/pages/readers/SourcePage.jsx` |
| Document Reader | `http://localhost:5173/documents/reader` | Upload card, file list with actions, document preview modal, processing status, upload history | DocumentReaderPage, UploadCard, FileList, DocumentPreview, ProcessingStatus, UploadHistory, documentApi, sourceApi | `src/pages/readers/DocumentReaderPage.jsx`, `src/components/upload/*`, `src/services/documentApi.js` |
| Website Index | `http://localhost:5173/website` | URL input, index button, progress placeholder | SourcePage (website config), URLInput, Button, Progress | `src/pages/readers/SourcePage.jsx`, `src/components/forms/URLInput.jsx` |
| Website Reader | `http://localhost:5173/website/reader` | Add website form, stats cards, transcript/summary panels, indexed sites list, preview, metadata, processing status, history | WebsiteReaderPage, URLInput, WebsitePreview, WebsiteHistory, SourceMetadata, WebsiteProcessingStatus, websiteSourceApi | `src/pages/readers/WebsiteReaderPage.jsx`, `src/components/readers/*`, `src/services/websiteSourceApi.js` |
| YouTube Index | `http://localhost:5173/youtube` | YouTube URL input, index button, progress placeholder | SourcePage (youtube config), YouTubeURLInput, Button, Progress | `src/pages/readers/SourcePage.jsx`, `src/components/forms/YouTubeURLInput.jsx` |
| YouTube Reader | `http://localhost:5173/youtube/reader` | Add video form, stats cards, transcript/summary panels, indexed videos list, preview, metadata, processing status, history, retry | YouTubeReaderPage, YouTubeURLInput, YouTubePreview, YouTubeHistory, YouTubeSourceMetadata, YouTubeProcessingStatus, TranscriptPanel, SummaryPanel, youtubeSourceApi | `src/pages/readers/YouTubeReaderPage.jsx`, `src/components/readers/*`, `src/services/youtubeSourceApi.js` |

---

## Chat Routes (DashboardLayout)

| Route | URL | Expected Behavior | Components Involved | Files Responsible |
|-------|-----|-------------------|---------------------|-------------------|
| Chat | `http://localhost:5173/chat` | Chat window with welcome message, prompt input, streaming responses, citations, starter prompts, attachments | ChatPage, ChatWindow, ChatBubble, PromptInput, TypingIndicator, StreamingIndicator, EmptyState, FilePreviewGrid | `src/pages/readers/ChatPage.jsx`, `src/components/chat/*` |
| New Chat | `http://localhost:5173/chat/new` | Same as `/chat` (reuses ChatPage component) | ChatPage | `src/pages/readers/ChatPage.jsx` |

---

## Error Routes

| Route | URL | Expected Behavior | Components Involved | Files Responsible |
|-------|-----|-------------------|---------------------|-------------------|
| 404 Not Found | Any invalid route | Friendly 404 page with home/dashboard links | NotFound, Button, Link | `src/pages/errors/NotFound.jsx` |
| Error Boundary | Any unhandled error | Error display with retry and home buttons | ErrorBoundary, Button, Link | `src/pages/errors/ErrorBoundary.jsx` |

---

## Layout Components

### GlobalLayout (`src/layouts/GlobalLayout.jsx`)
- Used for: `/`, `/login`, `/signup`, `/forgot-password`, `/reset-password`
- Contains: Header with logo, navigation, auth buttons, theme toggle; Main with PageTransition; Footer; Toaster

### DashboardLayout (`src/components/layout/DashboardLayout.jsx`)
- Used for: All `/dashboard/*`, `/documents*`, `/website*`, `/youtube*`, `/chat*`
- Contains: Sidebar (collapsible, responsive), Navbar (search, theme, notifications, user menu), Main with PageTransition, Toaster

---

## Key Components by Category

### Sidebar (`src/components/layout/Sidebar.jsx`)
- Navigation: Dashboard, Workspaces, Chats, Search, Notifications, History, Documents, YouTube, Websites, Chat
- Actions: New Workspace, New Chat
- User section: Avatar, dropdown with Profile, Settings, Theme (Light/Dark/System), Sign out
- Mobile: Collapse toggle, close button
- Animations: Framer Motion (slide, fade, stagger)

### Navbar (`src/components/layout/Navbar.jsx`)
- Mobile menu button (hamburger)
- Desktop search bar (⌘K)
- Theme toggle dropdown
- Notifications dropdown with badge
- User menu dropdown (Profile, Account, Billing, Theme, Sign out)

### Theme System (`src/context/ThemeContext.jsx`)
- Modes: light, dark, system
- Persists to localStorage
- Listens to system preference changes
- No flash on mount (mounted state)

### Authentication (`src/context/AuthContext.jsx`)
- Login/register with JWT tokens
- Token refresh interceptor
- Persists to localStorage
- Mock API endpoints (ready for backend integration)

### API Layer (`src/services/api.js`)
- Axios instance with interceptors
- Access/refresh token management
- Automatic token refresh on 401
- Error handling utilities

---

## Responsive Breakpoints

| Breakpoint | Range | Sidebar Behavior |
|------------|-------|------------------|
| Mobile | < 640px | Hidden by default, slide-in on menu click |
| Tablet | 641px - 1024px | Hidden by default, slide-in on menu click |
| Laptop | 1025px - 1280px | Visible by default, collapsible to 64px |
| Desktop | > 1280px | Visible by default, collapsible to 64px |

---

## Theme Testing Checklist

- [ ] Light mode: All pages render with light colors
- [ ] Dark mode: All pages render with dark colors  
- [ ] System mode: Follows OS preference
- [ ] Theme persists after reload
- [ ] Theme toggle in Sidebar works
- [ ] Theme toggle in Navbar works
- [ ] Theme toggle in Settings works
- [ ] No flash on initial load

---

## Accessibility Checklist

- [ ] Keyboard navigation works on all interactive elements
- [ ] Focus visible states present
- [ ] ARIA labels on icon buttons
- [ ] Semantic HTML structure
- [ ] Form labels associated with inputs
- [ ] Error messages announced (role="alert")
- [ ] Skip link present (in globals.css)
- [ ] Reduced motion respected

---

## Form Validation Checklist

- [ ] Login: Email required, valid format; Password required, min 8 chars
- [ ] Signup: Name required, min 2 chars; Email required, valid; Password requirements (upper, lower, number); Confirm matches
- [ ] Forgot Password: Email required, valid format
- [ ] Reset Password: Password requirements; Confirm matches
- [ ] Search: Empty state handled
- [ ] URL inputs: Valid URL format, http/https only
- [ ] YouTube URL: Valid YouTube format detection

---

## API Integration Status

All API services use mock implementations when `VITE_API_BASE_URL` is not set or `VITE_USE_MOCK_API=true`. Ready for backend integration by:

1. Setting `VITE_API_BASE_URL` in `.env`
2. Implementing actual endpoints matching the service interfaces
3. Removing mock fallbacks in `youtubeSourceApi.js`, `websiteSourceApi.js`, `documentApi.js`, `auth.js`

---

## Known Limitations (Mock Implementation)

- Authentication uses localStorage only (no real backend)
- Document upload/processing simulates API calls
- Website/YouTube indexing simulates async processing
- Chat responses are simulated with keyword matching
- History/Notifications/Team data is static mock data
- Analytics charts are placeholders
- Settings changes persist only to localStorage

---

## Testing Commands

```bash
# Development server
npm run dev

# Production build
npm run build

# Lint check
npm run lint

# Type check
npm run typecheck

# Preview production build
npm run preview
```

---

## Files Modified in Phase 16 Recovery

### Routing
- `src/routes/index.jsx` - Added index routes for `/website` and `/youtube`, added `/chat/new` route

### Layout
- `src/components/layout/DashboardLayout.jsx` - Fixed sidebar visibility on desktop (open by default)
- `src/components/layout/Sidebar.jsx` - Added Documents, YouTube, Websites, Chat navigation items; fixed conflicting transform style

### Dashboard
- `src/pages/dashboard/DashboardPage.jsx` - Added `add-youtube` quick action handler
- `src/components/dashboard/QuickActions.jsx` - Added YouTube quick action with Video icon

### Components
- `src/components/forms/YouTubeURLInput.jsx` - Validates YouTube URLs
- `src/components/forms/URLInput.jsx` - Validates website URLs
- `src/components/upload/UploadCard.jsx` - Drag & drop file upload with progress

---

## Verification Status

✅ Build passes (`npm run build`)
✅ Lint passes (`npm run lint`)
✅ All routes defined and accessible
✅ Sidebar visible on desktop
✅ Navbar functional
✅ YouTube uploader accessible at `/youtube` and `/youtube/reader`
✅ Website uploader accessible at `/website` and `/website/reader`
✅ Document uploader accessible at `/documents` and `/documents/reader`
✅ Dashboard layout working
✅ Theme switching (light/dark/system)
✅ Mobile responsiveness
✅ Form validation
✅ Error boundaries
✅ 404 handling
