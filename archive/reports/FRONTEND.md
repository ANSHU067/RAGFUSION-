# FRONTEND.md

# DOCPRO V2 / RAGFusion AI
## Frontend Documentation

---

# 1. Introduction

The frontend of **DOCPRO V2 (RAGFusion AI)** is designed to provide a clean, modern, and intuitive user experience for interacting with AI-powered Retrieval-Augmented Generation (RAG).

The application allows users to:

- Upload Documents
- Index Websites
- Process YouTube Videos
- Chat with indexed knowledge
- Manage conversations
- Configure AI settings

The frontend focuses on simplicity, responsiveness, and productivity while hiding the complexity of the backend RAG pipeline.

---

# 2. Frontend Goals

The frontend should provide:

- Modern UI
- Responsive Design
- Fast Navigation
- Minimal Learning Curve
- Interactive Chat Experience
- Smooth Animations
- Scalable Component Architecture

---

# 3. Technology Stack

## Framework

- React
- Vite
- TypeScript

## Styling

- Tailwind CSS
- shadcn/ui
- Framer Motion

## Routing

- React Router DOM

## State Management

- React Context
- React Hooks

## API Communication

- Axios

## Icons

- Lucide React

---

# 4. Folder Structure

```text
src/
│
├── assets/
│
├── components/
│   ├── ui/
│   ├── common/
│   ├── dashboard/
│   ├── chat/
│   ├── auth/
│   ├── upload/
│   └── settings/
│
├── pages/
│   ├── Landing/
│   ├── Login/
│   ├── Signup/
│   ├── Dashboard/
│   ├── Documents/
│   ├── Website/
│   ├── YouTube/
│   ├── Settings/
│   └── Profile/
│
├── layouts/
│
├── routes/
│
├── hooks/
│
├── context/
│
├── services/
│
├── utils/
│
├── constants/
│
├── types/
│
├── App.tsx
│
└── main.tsx
```

---

# 5. Application Flow

```
Landing Page

↓

Login / Signup

↓

Dashboard

↓

Choose Knowledge Source

↓

Document
Website
YouTube

↓

Upload File / URL

↓

Knowledge Indexing

↓

Chat Interface

↓

Ask Questions

↓

Receive AI Response

↓

Save Conversation

↓

Logout
```

---

# 6. Pages

## Landing Page

Purpose

- Introduce the application
- Explain features
- Allow users to Login or Signup

Sections

- Navigation
- Hero
- Features
- Workflow
- Footer

---

## Login Page

Components

- Email
- Password
- Remember Me
- Login Button
- Forgot Password

---

## Signup Page

Components

- Name
- Email
- Password
- Confirm Password
- Signup Button

---

## Dashboard

The dashboard acts as the entry point after authentication.

Contains

- Sidebar
- Workspace
- Recent Conversations
- Source Selection
- User Profile

---

## Document Reader

Allows users to upload documents.

Features

- Drag & Drop
- Browse Files
- File Preview
- Upload Status
- Delete File

Supported Formats

- PDF
- DOCX
- TXT
- Markdown

---

## Website Reader

Allows users to index websites.

Components

- URL Input
- Validate URL
- Crawl Website
- Progress Indicator

---

## YouTube Reader

Allows users to process YouTube videos.

Components

- Video URL
- Transcript Status
- Index Button
- Loading Indicator

---

## Chat Interface

Main AI interaction page.

Layout

```
---------------------------------------------

Header

---------------------------------------------

Conversation

---------------------------------------------

AI Message

User Message

AI Message

---------------------------------------------

Input Box

Send Button

---------------------------------------------
```

Features

- Streaming Responses
- Markdown Support
- Code Highlighting
- Citations
- Copy Response

---

## Chat History

Displays

- Previous Conversations
- Search
- Rename
- Delete

---

## Settings

Contains

Appearance

- Dark Mode
- Light Mode
- Theme

AI

- Model
- Temperature
- Max Tokens
- Top-K

---

## Profile

Contains

- User Avatar
- Name
- Email
- Logout

---

# 7. Dashboard Layout

```
------------------------------------------------------------

Sidebar

Dashboard

Documents

Website

YouTube

History

Settings

Logout

------------------------------------------------------------

Top Navigation

------------------------------------------------------------

Main Content

------------------------------------------------------------
```

---

# 8. Sidebar Navigation

Items

- Dashboard
- Documents
- Website
- YouTube
- Chat History
- Settings
- Logout

---

# 9. Knowledge Source Selection

Users can select one of three supported sources.

```
+------------------+

📄 Document Reader

+------------------+

+------------------+

🌐 Website Reader

+------------------+

+------------------+

🎥 YouTube Reader

+------------------+
```

---

# 10. Upload Workflow

```
User Upload

↓

Validation

↓

Uploading

↓

Processing

↓

Chunking

↓

Embedding

↓

Index Complete
```

---

# 11. Chat Workflow

```
User Question

↓

API Request

↓

Streaming Response

↓

Display Answer

↓

Show Citations

↓

Save Conversation
```

---

# 12. Components

## Navigation

- Navbar
- Sidebar
- Breadcrumb

---

## Authentication

- Login Form
- Signup Form

---

## Upload

- Upload Card
- Drag & Drop
- File Card

---

## Chat

- Chat Window
- Message Bubble
- Markdown Renderer
- Typing Indicator
- Prompt Suggestions

---

## UI

- Button
- Input
- Textarea
- Card
- Modal
- Dialog
- Dropdown
- Toast
- Loader
- Skeleton
- Tooltip

---

# 13. State Management

Global State

- User
- Authentication
- Theme
- Current Workspace
- Current Source
- Current Conversation

Local State

- Form Inputs
- Upload Progress
- Loading States
- Search Query

---

# 14. Responsive Design

Supported Devices

- Mobile
- Tablet
- Desktop
- Ultra-wide Screens

Breakpoints

- Mobile
- Tablet
- Laptop
- Desktop

---

# 15. Animations

Use Framer Motion for:

- Page Transitions
- Sidebar Animation
- Card Hover
- Modal Animation
- Loading Screens
- AI Typing Indicator

---

# 16. Error Handling

Frontend should display user-friendly errors for:

- Invalid Login
- Upload Failure
- Invalid URL
- Network Error
- AI Timeout
- Empty Response

---

# 17. Accessibility

Requirements

- Keyboard Navigation
- Focus States
- ARIA Labels
- Screen Reader Support
- High Contrast Support

---

# 18. Future Enhancements

- Multi-Workspace Support
- Multi-Document Chat
- Voice Input
- Speech Output
- AI Agent Mode
- Drag & Drop Everywhere
- OCR Upload
- Image Chat
- Export Chat
- Share Conversations
- Team Collaboration
- Real-Time Notifications
- Offline Support
- Progressive Web App (PWA)

---

# 19. Frontend Development Checklist

- [ ] Landing Page
- [ ] Login
- [ ] Signup
- [ ] Dashboard
- [ ] Sidebar
- [ ] Source Selection
- [ ] Document Reader
- [ ] Website Reader
- [ ] YouTube Reader
- [ ] Upload Components
- [ ] Loading Screens
- [ ] Chat Interface
- [ ] Streaming Responses
- [ ] Citations UI
- [ ] Conversation History
- [ ] Settings
- [ ] Profile
- [ ] Responsive Design
- [ ] Animations
- [ ] API Integration
- [ ] Testing

---

# 20. Final Frontend User Flow

```
Landing Page
      │
      ▼
Login / Signup
      │
      ▼
Dashboard
      │
      ▼
Choose Source
 ├── 📄 Documents
 ├── 🌐 Website
 └── 🎥 YouTube
      │
      ▼
Upload / Enter URL
      │
      ▼
Knowledge Indexing
      │
      ▼
AI Chat Interface
      │
      ▼
Ask Questions
      │
      ▼
Receive AI Response
      │
      ▼
View Citations
      │
      ▼
Save Conversation
      │
      ▼
Logout
```

---

## Version

**Frontend Version:** 1.0.0

**Project:** DOCPRO V2 / RAGFusion AI

**Status:** Frontend Design & Development Specification