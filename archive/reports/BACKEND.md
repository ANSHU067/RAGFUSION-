# BACKEND.md

# DOCPRO V2 / RAGFusion AI
## Backend Documentation

---

# 1. Introduction

The backend is the core engine of **DOCPRO V2 (RAGFusion AI)**. It is responsible for processing user inputs, indexing knowledge sources, retrieving relevant context, interacting with Large Language Models (LLMs), and managing conversations.

The backend follows a modular architecture, making it scalable, maintainable, and easy to extend with additional AI models, retrieval techniques, or knowledge sources.

---

# 2. Backend Goals

The backend is designed to:

- Process Documents, Websites, and YouTube Videos
- Build a Retrieval-Augmented Generation (RAG) pipeline
- Generate embeddings
- Store vectors efficiently
- Retrieve relevant context
- Stream AI responses
- Manage conversations
- Support multiple AI models
- Provide a scalable API for the frontend

---

# 3. Technology Stack

## Language

- Python 3.11+

---

## Framework

- FastAPI

---

## AI Framework

- LangChain
- LangGraph

---

## LLM Providers

- Groq
- OpenAI
- NVIDIA NIM
- Ollama
- Anthropic
- Gemini

---

## Embedding Models

- sentence-transformers
- BAAI Embeddings
- NVIDIA Embeddings

---

## Vector Database

- ChromaDB

Future Support

- Pinecone
- Weaviate
- Qdrant
- PGVector

---

## Database

- PostgreSQL

---

## Authentication

- JWT
- OAuth (Future)

---

## Task Queue

- Celery (Future)

---

# 4. Backend Architecture

```
Frontend

↓

FastAPI

↓

Authentication

↓

API Router

↓

Business Logic

↓

RAG Pipeline

↓

Vector Database

↓

LLM

↓

Response

↓

Frontend
```

---

# 5. Folder Structure

```text
backend/

├── app/
│
├── api/
│   ├── auth/
│   ├── documents/
│   ├── website/
│   ├── youtube/
│   ├── chat/
│   ├── history/
│   └── settings/
│
├── core/
│
├── config/
│
├── database/
│
├── models/
│
├── schemas/
│
├── services/
│
├── rag/
│
├── vectorstore/
│
├── embeddings/
│
├── llm/
│
├── loaders/
│
├── chunking/
│
├── prompts/
│
├── middleware/
│
├── utils/
│
├── tests/
│
├── main.py
│
└── requirements.txt
```

---

# 6. Backend Workflow

```
Client Request

↓

API Endpoint

↓

Validation

↓

Authentication

↓

Business Logic

↓

Knowledge Retrieval

↓

LLM

↓

Response Formatting

↓

JSON Response
```

---

# 7. API Modules

## Authentication

Responsible for

- Login
- Signup
- Logout
- JWT Token
- Refresh Token

---

## Documents

Responsible for

- Upload Files
- Delete Files
- File Validation
- Metadata Extraction

---

## Website

Responsible for

- URL Validation
- Website Crawling
- HTML Cleaning
- Text Extraction

---

## YouTube

Responsible for

- URL Validation
- Transcript Extraction
- Metadata Collection

---

## Chat

Responsible for

- User Prompt
- Retrieval
- LLM Response
- Streaming

---

## History

Responsible for

- Save Chats
- Delete Chats
- Rename Chats
- Retrieve Chats

---

## Settings

Responsible for

- Model Selection
- Temperature
- Retrieval Parameters

---

# 8. Document Processing Pipeline

```
Upload File

↓

Validate File

↓

Extract Text

↓

Clean Text

↓

Chunk Text

↓

Generate Embeddings

↓

Store in Vector Database

↓

Ready
```

---

# 9. Website Processing Pipeline

```
Website URL

↓

Validate URL

↓

Download HTML

↓

Remove Noise

↓

Extract Content

↓

Chunk

↓

Embeddings

↓

Vector Database
```

---

# 10. YouTube Processing Pipeline

```
YouTube URL

↓

Extract Video ID

↓

Download Transcript

↓

Extract Metadata

↓

Chunk

↓

Embeddings

↓

Store
```

---

# 11. RAG Pipeline

```
User Question

↓

Embedding

↓

Similarity Search

↓

Retrieve Context

↓

Reranking (Future)

↓

Prompt Builder

↓

LLM

↓

Streaming Response
```

---

# 12. Vector Database

Responsibilities

- Store Embeddings
- Store Metadata
- Similarity Search
- Delete Embeddings
- Update Embeddings

Supported Metadata

- Source
- File Name
- Website URL
- YouTube URL
- Page Number
- Timestamp
- Chunk ID

---

# 13. Embedding Layer

Responsibilities

- Convert Text into Vectors
- Generate Query Embeddings
- Batch Processing
- Embedding Cache

---

# 14. Prompt Engineering

Prompt Structure

```
System Prompt

↓

Retrieved Context

↓

Conversation History

↓

User Prompt

↓

LLM
```

Responsibilities

- Prompt Templates
- Dynamic Prompt Building
- Citation Formatting
- Context Injection

---

# 15. LLM Layer

Supported Providers

- Groq
- OpenAI
- NVIDIA NIM
- Ollama
- Anthropic
- Gemini

Responsibilities

- Chat Completion
- Streaming
- Tool Calling
- Function Calling
- Response Formatting

---

# 16. Conversation Management

Responsibilities

- Save Conversations
- Load Conversations
- Delete Conversations
- Rename Conversations
- Search Conversations

---

# 17. API Endpoints

## Authentication

```
POST   /auth/login
POST   /auth/signup
POST   /auth/logout
POST   /auth/refresh
```

---

## Documents

```
POST   /documents/upload
GET    /documents
DELETE /documents/{id}
```

---

## Website

```
POST   /website/index
GET    /website
DELETE /website/{id}
```

---

## YouTube

```
POST   /youtube/index
GET    /youtube
DELETE /youtube/{id}
```

---

## Chat

```
POST /chat
POST /chat/stream
```

---

## History

```
GET /history
GET /history/{id}
DELETE /history/{id}
PUT /history/{id}
```

---

## Settings

```
GET /settings
PUT /settings
```

---

# 18. Error Handling

The backend should gracefully handle:

- Invalid File Upload
- Invalid URLs
- Missing Transcript
- Vector Database Failure
- LLM Failure
- Authentication Failure
- Timeout Errors
- API Rate Limits

---

# 19. Security

Authentication

- JWT Authentication
- Password Hashing
- Session Management

Validation

- Input Validation
- URL Validation
- File Validation

Security Features

- Rate Limiting
- CORS
- API Key Management
- HTTPS
- Secure Environment Variables

---

# 20. Logging

Log

- API Requests
- Upload Events
- LLM Calls
- Errors
- Warnings
- User Activity

---

# 21. Performance Optimisation

- Async API Endpoints
- Streaming Responses
- Embedding Cache
- Batch Processing
- Lazy Loading
- Background Processing
- Vector Cache
- Connection Pooling

---

# 22. Testing

Unit Tests

- Authentication
- Upload
- Retrieval
- LLM
- API

Integration Tests

- Complete RAG Pipeline
- Upload to Chat
- Multi-source Retrieval

Performance Tests

- Large PDF
- Large Website
- Long Conversation
- Concurrent Users

---

# 23. Future Enhancements

- Multi-Agent Architecture
- Agentic Workflows
- MCP Integration
- Knowledge Graph Support
- Hybrid Search
- BM25 + Vector Search
- Cross-Encoder Reranking
- Long-Term Memory
- Background Indexing
- OCR Pipeline
- Image Understanding
- Audio Processing
- Video Processing
- Plugin System

---

# 24. Complete Backend Flow

```
User Request
      │
      ▼
FastAPI Router
      │
      ▼
Authentication
      │
      ▼
Request Validation
      │
      ▼
Business Logic
      │
      ▼
Source Loader
      │
      ├────────── Document Loader
      │
      ├────────── Website Loader
      │
      └────────── YouTube Loader
      │
      ▼
Text Cleaning
      │
      ▼
Chunking
      │
      ▼
Embedding Generation
      │
      ▼
Vector Database
      │
      ▼
Similarity Search
      │
      ▼
Prompt Builder
      │
      ▼
LLM
      │
      ▼
Streaming Response
      │
      ▼
Response Formatter
      │
      ▼
Frontend
```

---

## Version

**Backend Version:** 1.0.0

**Project:** DOCPRO V2 / RAGFusion AI

**Status:** Backend Architecture & Development Specification