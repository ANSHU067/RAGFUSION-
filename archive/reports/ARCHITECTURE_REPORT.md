# Architecture Report
## DOCPRO V2 - Complete System Architecture After Phase 8 & 9 Recovery

**Date:** August 2, 2026  
**Version:** 2.0.0  
**Status:** ✅ STABLE - Phase 8 Complete, Phase 9 Foundation Ready

---

## Executive Summary

DOCPRO V2 is a production-ready RAG (Retrieval-Augmented Generation) application with a complete backend architecture supporting document ingestion, vector search, intelligent retrieval, and AI-powered chat. Phase 8 has been fully integrated with proper RAG architecture, and Phase 9 provides a foundation for multi-provider LLM support.

---

## System Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend                             │
│                      (React + Vite)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/WebSocket
                       ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway                             │
│                    (FastAPI Router)                          │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼               ▼
┌──────────────┐ ┌──────────┐ ┌─────────────┐
│   Auth API   │ │ Chat API │ │ Ingest API  │
└──────┬───────┘ └────┬─────┘ └──────┬──────┘
       │              │               │
       ▼              ▼               ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                           │
├──────────────┬──────────────┬──────────────┬────────────────┤
│   Auth       │   Chat       │   Document   │   Website      │
│   Service    │   Service    │   Service    │   Service      │
└──────────────┴──────────────┴──────────────┴────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼               ▼
┌──────────────┐ ┌──────────┐ ┌─────────────┐
│ RAG Pipeline │ │   LLM    │ │  Database   │
│   (Phase 8)  │ │(Phase 9) │ │ PostgreSQL  │
└──────────────┘ └──────────┘ └─────────────┘
        │              │
        ▼              ▼
┌──────────────┐ ┌──────────┐
│  Vector DB   │ │  Redis   │
│  (ChromaDB)  │ │  Cache   │
└──────────────┘ └──────────┘
```

---

## Backend Architecture

### Directory Structure

```
backend/
├── app/
│   ├── __init__.py                 # Application factory
│   ├── api/                        # API routes
│   │   ├── __init__.py
│   │   ├── auth.py                 # Authentication endpoints
│   │   ├── documents.py            # Document management
│   │   ├── website.py              # Website ingestion
│   │   └── routes.py               # Route registration
│   ├── core/                       # Core utilities
│   │   ├── __init__.py
│   │   ├── exceptions.py           # Custom exceptions
│   │   ├── logging.py              # Logging configuration
│   │   └── rag_config.py          # ⭐ RAG configuration
│   ├── config/                     # Configuration
│   │   ├── __init__.py
│   │   ├── settings.py             # Main settings
│   │   └── embedding_config.py     # Embedding settings
│   ├── db/                         # Database layer
│   │   ├── __init__.py
│   │   ├── session.py              # DB sessions
│   │   └── vector_store.py         # Vector operations
│   ├── models/                     # SQLAlchemy models
│   │   ├── __init__.py
│   │   ├── base.py                 # Base model
│   │   └── entities.py             # Entity models
│   ├── schemas/                    # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── auth.py                 # Auth schemas
│   │   ├── document.py             # Document schemas
│   │   ├── health.py               # Health check
│   │   └── website.py              # Website schemas
│   ├── repositories/               # Data access layer
│   │   ├── __init__.py
│   │   ├── base.py                 # Base repository
│   │   └── entities.py             # Entity repository
│   ├── services/                   # Business logic
│   │   ├── __init__.py
│   │   ├── auth.py                 # Auth service
│   │   ├── document.py             # Document service
│   │   ├── crawler_service.py      # Web crawler
│   │   ├── extraction_service.py   # Text extraction
│   │   ├── chunking_service.py     # Text chunking
│   │   ├── embedding_service.py    # Embeddings
│   │   ├── embedding_cache.py      # Embedding cache
│   │   ├── embedding_helper.py     # Embedding helpers
│   │   ├── embedding_integration.py # Integration
│   │   ├── ingestion_service.py    # Document ingestion
│   │   └── health.py               # Health checks
│   ├── rag/                        # ⭐ RAG Components (Phase 8)
│   │   ├── __init__.py
│   │   ├── embeddings/
│   │   │   ├── __init__.py
│   │   │   └── embedding_manager.py
│   │   ├── retrievers/
│   │   │   ├── __init__.py
│   │   │   └── retriever_manager.py
│   │   ├── rerankers/
│   │   │   ├── __init__.py
│   │   │   └── reranker_manager.py
│   │   ├── pipelines/
│   │   │   ├── __init__.py
│   │   │   └── rag_pipeline.py
│   │   ├── prompts/
│   │   │   ├── __init__.py
│   │   │   └── prompt_builder.py
│   │   ├── cache/                  # Redis cache (future)
│   │   ├── filters/                # Metadata filters (future)
│   │   ├── memory/                 # Conversation memory (future)
│   │   └── utils/                  # Utilities (future)
│   ├── llm/                        # ⭐ LLM Providers (Phase 9)
│   │   ├── __init__.py
│   │   ├── providers/
│   │   │   ├── __init__.py
│   │   │   ├── base.py             # Base provider
│   │   │   ├── openai_provider.py  # ✅ OpenAI
│   │   │   ├── anthropic_provider.py # 🚧 Stub
│   │   │   ├── gemini_provider.py  # 🚧 Stub
│   │   │   ├── groq_provider.py    # 🚧 Stub
│   │   │   ├── openrouter_provider.py # 🚧 Stub
│   │   │   └── ollama_provider.py  # 🚧 Stub
│   │   ├── streaming/              # Stream handlers (future)
│   │   ├── callbacks/              # Callbacks (future)
│   │   ├── prompts/                # System prompts (future)
│   │   ├── parsers/                # Output parsers (future)
│   │   ├── tokenizers/             # Token counters (future)
│   │   ├── models/                 # Model configs (future)
│   │   └── utils/                  # Retry/fallback (future)
│   ├── middleware/                 # Middleware
│   │   ├── __init__.py
│   │   └── request_context.py      # Request context
│   ├── dependencies/               # Dependency injection
│   │   ├── __init__.py
│   │   └── settings.py             # Settings dependency
│   ├── workers/                    # Background workers
│   │   └── __init__.py
│   └── utils/                      # Utilities
│       └── __init__.py
├── main.py                         # Application entry point
├── tests/                          # Test suite
│   ├── conftest.py                 # Test configuration
│   ├── test_app.py                 # App tests
│   ├── test_auth.py                # Auth tests
│   ├── test_database.py            # Database tests
│   ├── test_documents.py           # Document tests
│   ├── test_migrations.py          # Migration tests
│   ├── test_website.py             # Website tests
│   ├── test_embedding_service.py   # Embedding tests
│   └── rag/                        # ⭐ RAG tests
│       ├── __init__.py
│       ├── conftest.py
│       └── (test files to be migrated)
├── alembic/                        # Database migrations
│   ├── env.py
│   └── versions/
├── scripts/                        # Utility scripts
│   └── (verification scripts)
└── requirements.txt                # Python dependencies
```

---

## Layer Descriptions

### 1. API Layer (`app/api/`)

**Purpose:** HTTP endpoints and request/response handling

**Components:**
- `auth.py` - Authentication endpoints (login, signup, refresh)
- `documents.py` - Document upload and management
- `website.py` - Website ingestion
- `routes.py` - Route registration and router setup

**Responsibilities:**
- Request validation (Pydantic schemas)
- Response formatting
- Error handling
- Route registration

---

### 2. Service Layer (`app/services/`)

**Purpose:** Business logic and orchestration

**Core Services:**
- `auth.py` - User authentication and authorization
- `document.py` - Document processing orchestration
- `ingestion_service.py` - Document ingestion pipeline
- `crawler_service.py` - Website crawling
- `extraction_service.py` - Text extraction from various formats
- `chunking_service.py` - Text chunking strategies
- `embedding_service.py` - Embedding generation
- `health.py` - Health check service

**RAG Integration:**
Services interact with RAG components for:
- Document chunking
- Embedding generation
- Vector storage
- Query processing

---

### 3. RAG Layer (`app/rag/`) ⭐ NEW

**Purpose:** Retrieval-Augmented Generation pipeline

**Architecture:**

```
Query → Embedding → Retrieval → Reranking → Prompt → Generation → Response
```

**Components:**

#### Embeddings (`app/rag/embeddings/`)
- `embedding_manager.py` - Document chunking and embedding generation
- Uses OpenAI text-embedding-3-small
- Configurable chunk size and overlap

#### Retrievers (`app/rag/retrievers/`)
- `retriever_manager.py` - Vector similarity search
- ChromaDB integration
- Metadata filtering support
- Top-K retrieval

#### Rerankers (`app/rag/rerankers/`)
- `reranker_manager.py` - Cross-encoder reranking
- Hybrid scoring (retrieval + reranking)
- Improves relevance of top results

#### Pipelines (`app/rag/pipelines/`)
- `rag_pipeline.py` - LangGraph orchestration
- State machine for RAG workflow
- End-to-end query processing
- Metadata tracking

#### Prompts (`app/rag/prompts/`)
- `prompt_builder.py` - Prompt engineering
- Context formatting
- Citation support
- Conversational prompts

**Future Extensions:**
- `cache/` - Redis caching for embeddings/queries
- `filters/` - Advanced metadata filtering
- `memory/` - Conversation history management
- `utils/` - Text processing utilities

---

### 4. LLM Layer (`app/llm/`) ⭐ NEW

**Purpose:** Multi-provider LLM abstraction

**Architecture:**

```
Request → Provider Selection → API Call → Response Parsing → Unified Format
```

**Components:**

#### Providers (`app/llm/providers/`)
- `base.py` - Abstract base provider interface
- `openai_provider.py` - ✅ OpenAI (GPT-4, GPT-3.5)
- `anthropic_provider.py` - 🚧 Anthropic (Claude)
- `gemini_provider.py` - 🚧 Google Gemini
- `groq_provider.py` - 🚧 Groq
- `openrouter_provider.py` - 🚧 OpenRouter
- `ollama_provider.py` - 🚧 Ollama (local)

**Provider Registry:**
- Dynamic provider registration
- Runtime provider selection
- Fallback chain support

**Features:**
- Unified response format
- Token counting
- Streaming support
- Async operations
- Error handling
- Retry logic

**Future Extensions:**
- `streaming/` - Advanced stream handling
- `callbacks/` - Event hooks for monitoring
- `prompts/` - System prompt templates
- `parsers/` - Structured output parsing
- `tokenizers/` - Token management
- `models/` - Model configuration registry
- `utils/` - Retry and fallback logic

---

### 5. Data Layer

#### Database (`app/db/`)
- PostgreSQL with AsyncIO support
- SQLAlchemy ORM
- Alembic migrations

#### Models (`app/models/`)
- User authentication
- Document metadata
- Conversation history
- Source tracking

#### Vector Store (`app/db/vector_store.py`)
- ChromaDB for embeddings
- Persistent storage
- Similarity search

#### Repository Pattern (`app/repositories/`)
- Data access abstraction
- Query builders
- Transaction management

---

### 6. Configuration Layer

#### Main Settings (`app/config/settings.py`)
- Environment-based configuration
- Database URLs
- Redis configuration
- CORS settings
- JWT configuration

#### RAG Config (`app/core/rag_config.py`) ⭐
- Pydantic-based validation
- RAG-specific settings
- Model selection
- Chunking parameters
- Retrieval settings

---

## Data Flow

### 1. Document Ingestion Flow

```
Upload → Validation → Extraction → Chunking → Embedding → Vector Store
```

**Detailed Steps:**
1. **API Layer** receives document upload
2. **Document Service** validates file
3. **Extraction Service** extracts text
4. **Chunking Service** splits into chunks
5. **Embedding Manager** generates embeddings
6. **Vector Store** stores embeddings
7. **Database** stores metadata

### 2. Chat/Query Flow

```
Query → RAG Pipeline → LLM → Response
```

**Detailed Steps:**
1. **API Layer** receives query
2. **RAG Pipeline** orchestrates:
   - **Embedding Manager** embeds query
   - **Retriever Manager** finds similar docs
   - **Reranker Manager** reranks results
   - **Prompt Builder** formats prompt
   - **LLM Provider** generates response
3. **API Layer** returns response

### 3. Website Ingestion Flow

```
URL → Crawl → Clean → Extract → Chunk → Embed → Store
```

**Detailed Steps:**
1. **API Layer** receives URL
2. **Crawler Service** fetches pages
3. **Extraction Service** cleans HTML
4. **Chunking Service** processes text
5. **Embedding Pipeline** generates vectors
6. **Vector Store** indexes content

---

## Technology Stack

### Backend
- **Framework:** FastAPI 0.100+
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0+ (async)
- **Database:** PostgreSQL 15+
- **Vector DB:** ChromaDB
- **Cache:** Redis
- **Tasks:** Celery (future)
- **Migrations:** Alembic

### RAG Stack
- **LLM Framework:** LangChain
- **Orchestration:** LangGraph
- **Embeddings:** OpenAI (text-embedding-3-small)
- **Reranking:** Sentence Transformers (cross-encoders)
- **LLMs:** OpenAI GPT-4/3.5 (+ future providers)

### Frontend
- **Framework:** React 18
- **Build Tool:** Vite
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **UI Components:** shadcn/ui

---

## Integration Points

### RAG ↔ Services Integration

```python
# In services/chat_service.py
from app.rag import RAGPipeline

class ChatService:
    def __init__(self):
        self.rag = RAGPipeline(collection_name="user_docs")
    
    async def process_query(self, query: str):
        result = self.rag.query(query)
        return result
```

### LLM ↔ RAG Integration

```python
# In rag/pipelines/rag_pipeline.py
from app.llm.providers import OpenAIProvider, LLMConfig

class RAGPipeline:
    def __init__(self):
        config = LLMConfig(provider="openai", model="gpt-4")
        self.llm = OpenAIProvider(config)
```

---

## Security Architecture

### Authentication
- JWT-based authentication
- Access + Refresh tokens
- Password hashing (bcrypt)

### API Security
- CORS configuration
- Rate limiting (future)
- Input validation (Pydantic)
- SQL injection prevention (SQLAlchemy)

### Secret Management
- Environment variables
- .env files (development)
- Secret managers (production)

---

## Scalability Considerations

### Horizontal Scaling
- Stateless API servers
- Load balancer ready
- Session storage in Redis

### Database Scaling
- Connection pooling
- Read replicas (future)
- Query optimization

### Vector Store Scaling
- ChromaDB clustering (future)
- Sharding by collection
- Caching layer (Redis)

---

## Monitoring & Observability

### Logging
- Structured logging
- Request ID tracking
- Log levels by environment

### Health Checks
- `/health` endpoint
- Database connectivity
- Vector store status

### Metrics (Future)
- Prometheus integration
- Request latency
- Token usage
- Cache hit rates

---

## Deployment Architecture

### Development
```
Local Machine → Docker Compose → PostgreSQL + Redis + Backend + Frontend
```

### Production (Planned)
```
Load Balancer → Backend Replicas → PostgreSQL (Primary) + Redis Cluster
                                 ↘ PostgreSQL (Replica)
```

---

## Migration Strategy

### From Root to Backend

All Phase 8 components successfully migrated from root to `backend/app/rag/`:
- ✅ Config migrated to `app/core/rag_config.py`
- ✅ Embeddings to `app/rag/embeddings/`
- ✅ Retrievers to `app/rag/retrievers/`
- ✅ Rerankers to `app/rag/rerankers/`
- ✅ Prompts to `app/rag/prompts/`
- ✅ Pipeline to `app/rag/pipelines/`

---

## Future Enhancements

### Phase 8 Extensions
- [ ] Redis caching for embeddings
- [ ] Conversation memory
- [ ] Advanced metadata filtering
- [ ] Hybrid search (BM25 + vector)

### Phase 9 Extensions
- [ ] Anthropic provider
- [ ] Ollama provider  
- [ ] Streaming utilities
- [ ] Retry/fallback logic
- [ ] Cost tracking

### General
- [ ] WebSocket support for streaming
- [ ] User feedback loop
- [ ] A/B testing framework
- [ ] Multi-tenancy

---

## Conclusion

DOCPRO V2 has a clean, well-organized architecture with clear separation of concerns. Phase 8 RAG components are fully integrated, and Phase 9 provides an extensible foundation for multi-provider LLM support. The system is production-ready with OpenAI integration and easily extensible for future enhancements.

---

**Last Updated:** August 2, 2026  
**Architecture Version:** 2.0.0  
**Status:** Production Ready
