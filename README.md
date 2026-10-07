# RAGFUSION — Enterprise Multi-Source RAG Platform

[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-REST%20%2B%20SSE-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=111827)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-SPA-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-persistent%20vectors-F97316)](https://www.trychroma.com/)
[![Redis](https://img.shields.io/badge/Redis-distributed%20quotas-DC382D?logo=redis&logoColor=white)](https://redis.io/)
[![Groq](https://img.shields.io/badge/Groq-LLM%20inference-F55036)](https://console.groq.com/docs/overview)
[![MIT License intent](https://img.shields.io/badge/License-MIT%20%28intended%29-green.svg)](#license)

**One authenticated knowledge workspace for documents, YouTube transcripts, and public web pages.**

RAGFUSION extracts text from multiple sources, embeds it locally, retrieves passages relevant to a question, and supplies those passages to a language model with traceable source metadata. It combines a React workspace, a FastAPI API, PostgreSQL, persistent Chroma storage, Redis request controls, and Groq inference.

> **Implementation baseline:** This guide describes the code after Phases 1–5 of hardening and cleanup. The latest completed Phase 5 verification recorded **460 backend tests passed, 30 integration tests skipped, 51 frontend tests passed, and no broken Python requirements**. These are recorded results, not a production certification or a claim that every deployment has zero vulnerabilities.
>
> **Current versions and behavior:** The frontend manifest uses **React 19**, not the earlier React 18 baseline. Use **Node 24** for the current toolchain. The active Groq model defaults to **`openai/gpt-oss-120b`**, not Llama 3. Retrieved context is **character-bounded**. The SSE endpoint delivers chunks of a completed answer, while the current React chat uses the JSON endpoint. True provider-token streaming and tokenizer-aware context budgeting remain follow-up work.

## Contents

1. [Executive summary and capabilities](#1-executive-summary-and-capabilities)
2. [End-to-end architecture and data flow](#2-end-to-end-architecture-and-data-flow)
3. [Technology choices and engineering tradeoffs](#3-technology-choices-and-engineering-tradeoffs)
4. [Security and production hardening](#4-security-and-production-hardening)
5. [Active repository structure](#5-active-repository-structure)
6. [Technical interview defense](#6-technical-interview-defense)
7. [Getting started and local development](#7-getting-started-and-local-development)
8. [API guide](#8-api-guide)
9. [Testing, deployment, and operations](#9-testing-deployment-and-operations)

## 1. Executive Summary and Capabilities

### The problem RAGFUSION solves

A team's knowledge often lives in disconnected places: a PDF specification, a Word document, a video explanation, and a website containing newer details. A language model does not automatically know that private or recently published information. Sending every source in full with every question wastes context and computation.

**Retrieval-Augmented Generation (RAG)** adds a search step before generation. Instead of relying only on a model's training data, the application finds relevant source passages and includes them with the question.

A typical workflow is:

1. Upload a document, submit a captioned YouTube video, or register and process a public website.
2. Wait until the source is successfully indexed and ready.
3. Select one or more sources, or search all ready sources owned by the current user.
4. Ask a question.
5. Read the answer and inspect its accompanying source metadata.
6. Continue the conversation or reopen it from history.

### Core capabilities

- **Unified source retrieval:** PDF, DOCX, TXT, CSV, Markdown, YouTube captions, and public HTML pages enter a common text-search space.
- **Tenant-isolated application queries:** authenticated ownership and source readiness determine what can be retrieved and used as context.
- **Context-aligned citations:** citation metadata is derived from the exact chunks accepted into the prompt.
- **Resilient authentication lifecycle:** expiring access tokens, rotating refresh tokens, database-backed revocation, and coordinated frontend refresh requests.
- **Persistent conversations:** create, continue, rename, clear, and soft-delete chat sessions; inspect and restore history.
- **Local embeddings:** source text is encoded without calling a remote embedding service.
- **Bounded ingestion:** upload, extraction, crawler, and concurrency limits reduce resource-exhaustion risk.
- **Distributed request controls:** Redis coordinates quotas across API workers.
- **Efficient chat rendering:** isolated input drafts, memoized message components, stable callbacks, and a separately loaded 3D landing scene.

### Essential terminology

A **chunk** is a passage extracted from a source. An **embedding** is a numerical representation of that passage's meaning. A **vector store** searches these representations for semantic similarity. **Context** is the selected evidence sent to the language model. A **citation** records provenance for that evidence.

The platform is multi-source and is sometimes described as multi-modal. The active retrieval representation is text: it does not currently analyze video frames, perform image understanding, or transcribe raw audio.

Indexed websites are snapshots from ingestion time, not a live web search performed for every question. Updating source knowledge requires another ingestion or supported processing operation.

RAG improves access to evidence but does not eliminate hallucination. The current prompt permits general-knowledge answers when appropriate; this is not an evidence-only question-answering system.

## 2. End-to-End Architecture and Data Flow

### 2.1 Components and storage responsibilities

```mermaid
flowchart TB
    UI["React workspace"]
    API["FastAPI REST and SSE API"]
    AUTH["JWT validation and ownership checks"]
    LIMIT["Redis-backed request admission"]
    INGEST["Document, YouTube, and website services"]
    RAG["RAG orchestration"]
    EMB["Shared local MiniLM runtime"]
    SQL[("PostgreSQL: application state")]
    VECTOR[("Chroma: semantic index")]
    FILES[("Uploaded files")]
    GROQ["Groq inference API"]

    UI --> API
    API --> LIMIT
    API --> AUTH
    AUTH --> SQL
    API --> INGEST
    API --> RAG
    INGEST --> FILES
    INGEST --> SQL
    INGEST --> EMB
    EMB --> VECTOR
    RAG --> SQL
    RAG --> EMB
    RAG --> VECTOR
    RAG --> GROQ
    GROQ --> RAG
    RAG --> API
    API --> UI
```

**PostgreSQL** is the relational source of truth for users, ownership, source lifecycle, chunk records, settings, conversations, and messages.

**Chroma** is the semantic index. The active path uses a persistent `rag_documents` collection containing text, vectors, and provenance metadata. User isolation is enforced through authorized source predicates and application checks; there is not a separate collection for every tenant.

**Uploaded files** are stored under server-generated paths. The client filename is display metadata, not a trusted filesystem path.

**Redis** is the active shared rate-limit store. Local model and embedding caches are separate from Redis request quotas; the existence of cache utility modules does not imply every chat response is Redis-cached.

### 2.2 Ingestion pipeline

```mermaid
flowchart LR
    DOC["PDF / DOCX / TXT / CSV / Markdown"] --> DV["Bound upload before multipart parsing; inspect bytes"]
    YT["YouTube URL"] --> YV["Validate video identity; retrieve captions"]
    WEB["Public website URL"] --> WV["URL validation and connector DNS/IP checks"]
    WV --> FETCH["Bounded HTTP fetch; HTML text extraction"]
    DV --> TEXT["Extract and normalize text"]
    YV --> TEXT
    FETCH --> TEXT
    TEXT --> CHUNKS["Source-specific chunking and limits"]
    CHUNKS --> EMB["Shared MiniLM embeddings: 384 dimensions"]
    CHUNKS --> SQL[("SQL source and chunk records")]
    EMB --> CHROMA[("Persistent Chroma index")]
    SQL --> READY["Publish ready source state"]
    CHROMA --> READY
```

SQL and Chroma are separate stores. The diagram does not imply a single atomic transaction across them.

#### Documents

`POST /api/v1/documents/upload` validates transport size before multipart parsing, saves bounded file reads, validates content, extracts text, chunks it, embeds it, and persists the results.

Supported formats are PDF, DOCX, TXT, CSV, and Markdown. PDF and DOCX undergo format-specific validation. Text formats undergo byte/encoding checks rather than relying on the browser-supplied MIME type.

Document processing rejects more than 2,000 chunks. Reprocessing replaces the existing document chunks and vectors, including removal of a previous generation's longer tail of chunks. Here, “generation” means an ingestion run; the current index does not contain generation-versioned publication metadata.

A source is reported ready only after the successful storage path completes. An HTTP `202` response does not imply the repository contains a durable external job queue: the current ingestion routes await substantial processing work.

#### YouTube

The active backend service parses the video URL, fetches available captions with `youtube-transcript-api`, cleans the transcript, and builds overlapping word windows. It records video/source identity and chunk offsets, then indexes the transcript in the same semantic space as documents and websites.

The active service flattens transcript segments into text. Its chunks carry word offsets, not preserved video timestamps. The separate `youtube_pipeline/` package contains timestamp-aware chunking and additional metadata extraction, but it is not the active API's implementation. Its embedding generator also owns a separate model instance.

No captions means no transcript ingestion through this path. Disabled captions, unavailable languages, external restrictions, and network errors are handled as ingestion failures; Whisper is not an automatic fallback.

#### Websites

`POST /api/v1/website/ingest` registers a URL. `POST /api/v1/website/{source_id}/process` claims it for processing, fetches a public HTML page, extracts readable text, chunks and embeds the content, and updates source readiness.

The active service processes a single page. Broader crawl utilities exist in the crawler module, but the routed service is not an unrestricted recursive browser crawler.

Scripts and HTML markup are removed from the text extraction path. This does not make the resulting prose trustworthy or immune to prompt injection.

### 2.3 Query, context, and response flow

```mermaid
flowchart TD
    Q["Authenticated user question"] --> SETTINGS["Resolve request, saved, and application settings"]
    SETTINGS --> SOURCES["Resolve live, ready, owned source IDs"]
    SOURCES --> EMB["Encode question in the same MiniLM space"]
    EMB --> RET["Per-modality over-fetch: up to 2 x top_k"]
    RET --> MERGE["Merge by ascending distance"]
    MERGE --> FILTER["Authorize, reject empty/invalid candidates, deduplicate"]
    FILTER --> TOP["Keep overall top_k"]
    TOP --> PACK["Pack complete chunks within character budget"]
    PACK --> IDS["Record exact included chunk IDs"]
    PACK --> LLM["Groq synchronous model invocation in worker execution"]
    LLM --> ANSWER["Completed answer"]
    IDS --> CITES["Citations from packed chunks only"]
    ANSWER --> JSON["JSON chat response"]
    CITES --> JSON
    ANSWER --> SSE["SSE content chunks, citations, completion"]
    CITES --> SSE
```

**Source authorization:** SQL determines which sources are ready and owned by the caller. Chroma receives authorized source predicates, and results are checked again before entering the prompt.

**Balanced retrieval:** when several source types are selected, each can return enough candidates to fill the entire request. For `top_k=5`, the pipeline can fetch ten candidates per active type, merge them, and select the best five overall. An empty YouTube result does not reserve an unused quota.

**Distance semantics:** lower Chroma distance is better in this path. Comparability depends on using the same embedding space and metric. This is candidate pooling, not a forced equal-share policy or reciprocal rank fusion.

**Reranking:** the graph contains a rerank stage, but the default pipeline has no active cross-encoder reranker. The stage passes through the retrieved candidates unless a reranker is supplied.

**Context packing:** `PackedContext` contains the accepted text and exact chunk identities. Oversized chunks are skipped, allowing later smaller chunks to fit. The default retrieved-context limit is 4,000 characters; history is separately bounded. This is not a tokenizer-aware budget for the full model input and output.

**Settings:** omitted chat controls remain unset. Resolution follows `Request override > User saved settings > Application default`. Resolved `top_k`, `temperature`, and `max_tokens` reach retrieval and generation; `temperature=0.0` remains valid.

### 2.4 Current streaming contract and intended evolution

The API exposes both `/chat` and `/chat/stream`. SSE frames carry JSON with content, citation, completion, or error information. The route checks disconnections between emitted chunks and sets headers intended to prevent proxy buffering.

The current implementation first generates the full answer, then emits 20-character pieces. The React chat calls the completed JSON endpoint. Consequently, this release should not be presented as direct, real-time provider-token streaming.

The target evolution is:

```mermaid
flowchart LR
    Q["Question and authorized retrieval"] --> B["Tokenizer-aware full prompt budget"]
    B --> G["Groq provider streaming iterator"]
    G --> S["SSE token relay"]
    B --> C["Exact packed-chunk citations"]
    S --> UI["Abortable browser stream reader"]
    C --> UI
```

This second diagram is a roadmap, not a description of implemented behavior. It requires provider stream integration, frontend consumption, cancellation propagation, and latency measurements.

## 3. Technology Choices and Engineering Tradeoffs

### FastAPI over Flask or Django

FastAPI matches a workload dominated by asynchronous database and network I/O. Pydantic v2 validates request and response contracts, dependency injection makes authentication and sessions explicit, and OpenAPI documentation is generated from the API schema. ASGI response handling provides the foundation for SSE.

Compared with a conventional synchronous Flask application, fewer additional conventions are needed for concurrent I/O. Django offers a rich application framework and admin ecosystem, but those features are not the center of this API-first architecture. Both remain valid alternatives; FastAPI is a workload fit, not a universal performance verdict.

CPU-bound parsing and embedding still require bounded worker execution. Declaring an endpoint `async` does not make synchronous library calls nonblocking or safely interruptible.

### React and Vite over Next.js

The frontend is an authenticated SPA with a separately deployed Python API. React provides reusable interactive components, while Vite supplies rapid development feedback and production bundling. The current manifest uses React 19 and Vite 8; older React 18 descriptions are historical.

This avoids introducing a server-rendering layer solely for private workspace screens. Client-side request orchestration, session invalidation, and Axios refresh coordination remain explicit. Next.js would become more attractive if server-rendered public content or search-engine discoverability became primary requirements.

HMR speed depends on the machine and project; no sub-second benchmark is established here. The current client controls ordinary abortable HTTP requests, with direct SSE consumption still to be implemented.

Tailwind CSS supplies consistent design primitives, Lucide provides icons, and React Markdown handles message presentation. Vitest and Testing Library cover session behavior, API handling, and rendering regressions.

### Local MiniLM over a cloud embedding API

`sentence-transformers/all-MiniLM-L6-v2` produces 384-dimensional vectors and runs locally. This removes external per-token embedding fees and external embedding-request latency after provisioning. It also keeps source text local during embedding.

The runtime uses a lock-protected model cache keyed by model and device. Concurrent initialization cannot create duplicate copies for the same key. The shared adapter supports batched encoding, and CPU is the active default.

The singleton is per process, not per deployment. More API workers can mean more model copies. Local embeddings still cost CPU, memory, and operational effort; they are not zero-latency computation. Selected context is later sent to Groq, so the complete RAG workflow is not offline.

The model is designed for sentences and short paragraphs and truncates input beyond 256 word pieces by default. Chunking should be evaluated against that encoder limit, independently of the LLM context limit. See the [MiniLM model card](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).

Cloud embeddings may offer better quality for a particular domain or simplify infrastructure. Choose using labeled retrieval evaluation, not cost claims alone. Changing models requires rebuilding a compatible index, even when two models have the same dimensionality.

### Groq over direct OpenAI or Anthropic integration

Groq is the active inference integration through `ChatGroq`. Its low-latency inference architecture is attractive for conversational workloads, but the application's current default is `openai/gpt-oss-120b`. Llama 3 and Mixtral are not the current construction-time defaults.

Provider selection should compare measured answer quality, cost, throughput, availability, and latency for representative prompts. Check model availability in the [Groq model catalog](https://console.groq.com/docs/models).

There is no project benchmark proving TTFT below 500 ms. Authentication, retrieval, context packing, network transit, and model generation all contribute to latency; buffered SSE further delays visible content. Provider marketing numbers are not application service-level objectives.

Saved provider/model labels do not automatically switch the shared pipeline's adapter. The active path remains Groq unless model construction and routing are explicitly changed.

### ChromaDB over Pinecone or Milvus

Chroma offers a persistent local semantic index with a small initial operational footprint. The embedded deployment needs no external vector-service account and integrates directly with the Python retrieval layer.

The active collection is shared, with source metadata filters and application authorization. SQLite-backed metadata and the accompanying persistent index files must be treated together as durable storage.

The tradeoffs are significant: embedded storage is not a distributed high-availability service, SQL and Chroma writes are not atomic together, and multi-host scaling requires a supported storage topology. Pinecone or a separately operated Milvus deployment can be more suitable when managed operations, replication, or scale justify the added infrastructure.

### PostgreSQL, SQLAlchemy Async, and Alembic

PostgreSQL enforces application relationships and stores the source lifecycle independently of approximate search. SQLAlchemy provides async sessions and bounded connection pooling. Sessions commit successful work, roll back failures, and close when their context exits.

The application caches its database engine and session factory. Network database pools use explicit sizing, pre-ping, timeout, and recycling settings. Pool capacity must be budgeted across all worker processes.

Alembic makes schema evolution explicit. The migration graph contains a historical merge and currently ends at `20261006_0001`. SQLite tests provide rapid feedback but cannot establish PostgreSQL row-locking guarantees.

### Redis sliding windows over in-memory quotas

Each in-memory worker would maintain an independent limit. Redis supplies shared state, so adding API workers does not multiply the intended quota.

One Lua script reads Redis time, removes expired sorted-set entries, checks capacity, records accepted requests, and sets key expiry atomically. Sequence numbers avoid collisions when requests arrive in the same millisecond. Related keys use a common cluster hash slot.

This exact sliding-window log avoids fixed-window boundary bursts at the cost of retaining recent request events. Failure to verify quotas returns a service-unavailable response. The explicit in-memory implementation is for test injection, not a production outage fallback.

This is application admission control, not complete network DDoS protection. It must be complemented by ingress limits and infrastructure capacity planning.

### youtube-transcript-api over Whisper

Existing captions can be fetched without downloading audio and running speech recognition. That avoids GPU-heavy transcription, model provisioning, and additional processing time for captioned videos.

Retrieval is not instantaneous or guaranteed: network conditions, language availability, disabled captions, and upstream restrictions still apply. Video metadata enrichment is a separate concern; the transcript library is not a universal metadata service.

Whisper would be a separately bounded fallback for videos without captions, with its own permissions, queue, resource limits, and failure handling.

### LangChain and LangGraph

LangChain supplies adapters, and LangGraph exposes retrieval, prompt construction, and generation as explicit stages with inspectable state. The application's authorization and lifecycle guarantees are implemented around those abstractions.

The cost is dependency coordination and additional abstraction. Requirements constrain the LangChain family to compatible pre-1.0 releases; `pip check` verifies installed dependency consistency. Framework adoption does not supply security or transactionality automatically.

## 4. Security and Production Hardening

### 4.1 SSRF defense matrix

The crawler treats every submitted destination as untrusted.

- **Scheme and syntax:** only HTTP/HTTPS; reject embedded credentials, invalid hosts, unsupported address syntax, and localhost names.
- **Literal IP checks:** reject private RFC 1918 ranges, loopback, link-local, multicast, unspecified, reserved, and other non-global addresses.
- **DNS checks:** validate every address returned to the actual HTTP connector, avoiding a separate unchecked connection lookup; disable connector DNS caching.
- **IPv6 transition checks:** inspect IPv4-mapped and 6to4 embedded addresses; reject Teredo destinations.
- **Cloud platform exclusions:** explicitly reject `169.254.169.254` and Azure WireServer `168.63.129.16`, including checked embedded-address forms.
- **Redirect policy:** redirects are disabled rather than followed to an unvalidated destination.
- **Proxy policy:** do not inherit environment proxy settings.
- **Response bounds:** enforce a 2 MiB ceiling while reading, regardless of `Content-Length`; reject compressed responses and bound connection/read/total time.
- **Extraction policy:** accept HTML for website processing and extract text without executing page JavaScript.

The Azure exclusion matters because that platform address can pass ordinary global-address classification. Deployment-level egress restrictions should reinforce the application checks.

### 4.2 Upload and extraction limits

Document ingestion applies these ceilings:

- File bytes: **15 MiB**, with a separate **64 KiB** multipart framing allowance.
- Document chunks: **2,000**.
- Extracted text: **8,000,000 characters**.
- PDF pages: **1,000**.
- DOCX declared expanded content: **32 MiB**.
- DOCX archive entries: **2,048**.

The configured document size may lower the hard limit, not raise it. Request size is bounded before multipart parsing, and file reads use bounded increments.

PDF validation checks the signature; DOCX validation checks the ZIP-based document and expansion limits; text formats undergo strict UTF-8 and binary-content checks. An ELF executable does not become an accepted text document merely because it is named `.txt` or declares `text/plain`.

These checks reduce known resource risks. They do not make arbitrary parser execution equivalent to a sandboxed, hard-killable worker process.

### 4.3 Patched PDF processing

The manifest requires:

```text
pypdf>=6.7.2
```

This is a minimum version constraint, not an exact version pin. Version 6.7.2 fixes CVE-2026-27628, an infinite-loop issue involving circular `/Prev` entries in PDF cross-reference streams. See the [pypdf maintainer advisory](https://github.com/py-pdf/pypdf/security/advisories/GHSA-2rw7-x74f-jg35).

Keep resolved dependencies updated and scanned. This fix addresses a specific advisory; `pip check` detects dependency incompatibility, not all security vulnerabilities.

### 4.4 Authentication and secret handling

The active implementation is `backend/app/services/auth.py`. It validates signed, expiring tokens against the user's database-backed `auth_version`. Refresh rotates the version, and logout invalidates previously issued tokens through a version change.

Production startup rejects empty, short, and known placeholder JWT secrets. The trimmed value must contain at least 32 characters. Generate it cryptographically; length alone is not entropy.

The frontend uses a shared in-flight refresh operation and session-version checks to prevent refresh storms and stale account responses. Tokens currently live in `localStorage`, so XSS prevention remains important. Raw HTML is not enabled in the current Markdown renderer.

The obsolete JWT manager and authentication middleware were removed in Phase 5; they are not alternate active authentication paths.

### 4.5 Vector lifecycle synchronization

Document deletion coordinates SQL records, Chroma vectors, and the physical file:

1. Authorize and serialize access to the owned document.
2. Capture its existing vector records for compensating recovery.
3. Remove document vectors using document identity and owner scope.
4. Commit the SQL deletion.
5. Remove the physical file after the SQL commit.

Normal failures attempt vector restoration and SQL rollback. A physical cleanup failure after commit is logged without pretending the SQL deletion was reversed.

Reprocessing removes old vectors before adding replacement chunks and replaces SQL chunk records under the document row lock. This prevents leftovers when the new document produces fewer chunks.

SQL and Chroma cannot share a transaction. Process crashes between stores still require reconciliation; generation-versioned publication and an outbox are not implemented. Live-source authorization additionally prevents deleted SQL sources from being accepted as chat evidence.

### 4.6 Citation integrity guard

The packer records exact accepted chunk IDs. Both prompt construction and citation generation consume that accepted set:

```text
Citation chunk identities ⊆ Chunk identities included in the prompt
```

A retrieved chunk omitted for space cannot retain a citation. If no chunks fit, the prompt includes a notice not to claim those sources were consulted.

The guarantee concerns the returned citation metadata. It does not prove that every generated claim is supported, or prevent the model from producing an incorrect textual attribution. The current packing bound is characters, not exact model tokens.

### 4.7 Distributed limits and dependency health

Default route-category quotas are per resolved client identity:

- Authentication: 7 requests per 60 seconds.
- Chat mutations: 30 requests per 60 seconds.
- Ingestion mutations: 10 requests per 60 seconds.
- General API traffic: 120 requests per 60 seconds.

Exhaustion returns `429`; Redis enforcement failure returns `503`. Forwarded identities are accepted only through explicitly trusted proxies. Health and CORS preflight are exempt.

Health uses the shared async Redis client and wraps its ping in a two-second timeout. It checks database and Redis connectivity, not full RAG readiness, external provider health, or model-cache availability.

### 4.8 Frontend performance and cleanup

Input drafts use an isolated context slice, so typing does not publish a new message-list value. Chat bubbles and Markdown rendering are memoized, and action callbacks remain stable. The conversation and composer share a centered width.

`HomePage` directly lazy-loads `HeroScene` behind Suspense. The common barrel no longer statically exports it, and Vite separates Three.js-related code into dedicated groups.

Memoization reduces repeated rendering; it does not virtualize an unlimited history. The unused history wrapper, obsolete document-status call, duplicate summary component, and unused backend provider stubs were removed during cleanup.

## 5. Active Repository Structure

This is a focused map of the current application and configuration files. Selected directories are expanded; generated data, virtual environments, dependencies, and historical material are omitted. Omission is not a statement that all such folders have been deleted: an `audits/` directory remains locally. Root Alembic and pytest configuration files also remain.

```text
RAGFUSION/
├── README.md
├── alembic.ini
├── pytest.ini
├── backend/
│   ├── .env.example
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── alembic.ini
│   ├── main.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── embeddings.txt
│   │   └── crawling.txt
│   ├── alembic/
│   │   ├── env.py
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── 20260801_0001_initial_schema.py
│   │       ├── 20260802_0002_rename_chat_session_metadata.py
│   │       ├── 20260802_0003_user_settings.py
│   │       ├── 20260803_0001_fix_processing_status.py
│   │       ├── 7efa7e63b3ce_merge_migration_heads.py
│   │       ├── 20261005_0001_storage_integrity.py
│   │       ├── 20261005_0002_auth_version.py
│   │       └── 20261006_0001_user_profile.py
│   ├── app/
│   │   ├── api/                 # Auth, documents, YouTube, web, chat, history
│   │   ├── config/              # Application and embedding configuration
│   │   ├── core/                # Shared model runtime, limits, security, RAG config
│   │   ├── db/                  # Async engine/session lifecycle
│   │   ├── dependencies/        # FastAPI dependency providers
│   │   ├── llm/
│   │   │   └── providers/       # Base interface and retained OpenAI adapter
│   │   ├── middleware/          # Upload limits, quotas, headers, request context
│   │   ├── models/              # Relational entities
│   │   ├── rag/
│   │   │   ├── embeddings/
│   │   │   ├── pipelines/       # Active Groq/LangGraph query path
│   │   │   ├── prompts/         # Context packing and accepted chunk IDs
│   │   │   ├── rerankers/
│   │   │   └── retrievers/      # Chroma adapters and document vector operations
│   │   ├── repositories/       # SQL access patterns
│   │   ├── schemas/            # Pydantic contracts
│   │   ├── services/           # Ingestion, auth, chat, history, health
│   │   ├── utils/
│   │   └── workers/
│   └── tests/
├── frontend/
│   ├── .env.example
│   ├── package.json
│   ├── package-lock.json
│   ├── vite.config.js
│   ├── vitest.config.js
│   ├── public/
│   ├── src/
│   │   ├── main.jsx
│   │   ├── components/
│   │   │   ├── chat/            # Bubbles, Markdown, citations, prompt input
│   │   │   ├── common/          # Lazy HeroScene and landing components
│   │   │   ├── readers/
│   │   │   ├── layout/
│   │   │   ├── ui/
│   │   │   └── upload/
│   │   ├── context/             # Auth, chat, isolated draft, theme state
│   │   ├── hooks/
│   │   ├── layouts/
│   │   ├── lib/
│   │   ├── pages/
│   │   ├── routes/
│   │   ├── services/            # Axios, sessions, historyApi, source clients
│   │   └── styles/
│   └── tests/
└── youtube_pipeline/
    ├── __init__.py
    ├── transcript_extractor.py
    ├── metadata_extractor.py
    ├── chunker.py
    ├── embedding_generator.py
    └── pipeline.py
```

The backend Docker build context is `backend/`; sibling repository folders are not copied into the API image. Its `.dockerignore` also excludes local secrets, tests, caches, and report files.

## 6. Technical Interview Defense

### Q1. Why use local MiniLM embeddings over cloud APIs?

It removes a remote dependency from embedding operations, avoids per-token embedding API charges, and keeps source text local during encoding. The cached runtime controls model initialization and supports batching.

The tradeoff is owning compute, memory, model distribution, and quality evaluation. I would compare recall at k, indexing throughput, latency percentiles, and total operating cost on a representative corpus before claiming it is better than a cloud model. The later Groq call still receives selected source content.

### Q2. How is SSRF prevented during web ingestion?

We validate URL syntax and the actual DNS results used by the connector. A public-looking hostname may resolve to an internal address, so checking the URL string alone is insufficient.

Private and platform addresses are rejected, redirects and environment proxies are disabled, and responses are bounded by size and time. Egress firewall rules provide an additional deployment boundary. The explicit WireServer exclusion covers an address that normal public/private classification can miss.

### Q3. How do you prevent orphaned vectors on deletion or reprocessing?

The document service scopes vector deletion by document and owner, coordinates it with SQL changes, and snapshots prior vectors for compensating recovery. Reprocessing purges the previous vector set before inserting replacements.

These stores do not share a transaction. Normal failures can be compensated; a crash between writes still needs reconciliation. A durable outbox, idempotent operation IDs, and generation-based index publication would strengthen recovery. I would not describe the current sequence as a distributed atomic commit.

### Q4. What happens if YouTube returns zero chunks in a multi-source query?

Each source type over-fetches candidates. The successful candidates are merged by distance and reduced to the overall k, so an empty source does not reserve an unusable quota.

If documents provide enough valid candidates, they can fill the entire result set. If fewer than k authorized, distinct candidates exist across all successful sources, returning fewer is correct. No finite over-fetch factor guarantees k results after arbitrary filtering.

### Q5. How do you guarantee citations match what the LLM saw?

The prompt packer returns both the context text and the exact accepted chunk identities. Citation generation uses that same accepted list rather than the original retrieval list.

This prevents citation metadata for chunks dropped during packing. It does not prove every generated sentence is entailed by those chunks. Claim-level verification and evidence-only abstention are separate product decisions.

### Q6. How did you optimize long chat conversations?

Draft keystrokes no longer update the context consumed by the message list. Memoized bubbles and Markdown renderers reuse output for unchanged props, while stable callbacks avoid invalidating those comparisons.

The optimization reduces repeated work. Extremely long histories still increase DOM size; virtualization and incremental loading are separate scaling measures. Tests should assert visible behavior and rendering boundaries rather than simply mirror hooks.

### Q7. Why Redis if FastAPI already has middleware?

Middleware is the enforcement location; Redis is the shared state authority. An in-memory dictionary cannot coordinate several API workers.

Atomic Lua makes admission one operation instead of a racy read-then-write sequence. Failing closed protects resources when shared quotas cannot be verified, at the cost of making Redis availability part of the service's availability budget.

### Q8. Is the streaming truly token-by-token, and is TTFT below 500 ms?

Not in the current implementation. The backend buffers the complete model response and then emits character chunks; the frontend uses the JSON endpoint.

The next step is a provider-stream-to-SSE relay with an abortable browser reader. Only after that should we measure client-visible p50/p95/p99 TTFT under representative retrieval and concurrency. A provider throughput claim is not an application latency guarantee.

### Q9. Are context limits token-aware?

Retrieved context currently uses a character budget. That provides a bound but is not exact for a model tokenizer, especially across languages and code.

A tokenizer-aware packer should reserve space for the system prompt, question, history, evidence, and output allowance. The embedding encoder's input limit must also be respected independently. A chunk can fit the LLM prompt while being truncated during embedding.

### Q10. Can RAG eliminate hallucination or prompt injection?

No. Retrieval provides evidence, but the model can misunderstand it or follow malicious instructions embedded in valid source text. The current prompt also permits general-knowledge answers.

Source validation protects ingestion and authorization; it does not make document content trusted instructions. Keep privileged actions outside model control, evaluate answer support, and define abstention behavior explicitly if the product requires evidence-only answers.

### Q11. How would you scale across machines?

Separate API connections, ingestion compute, database capacity, vector storage, and external provider quotas. Move ingestion to durable workers and choose a supported shared vector-service topology.

Budget model copies and database pools per process. Do not treat a shared filesystem mount of embedded Chroma as an automatic distributed database. Add load tests, reconciliation, and recovery drills before introducing multiple writers.

### Q12. Why not store vectors in PostgreSQL too?

That is a valid design alternative. A PostgreSQL vector extension could reduce cross-store coordination and simplify some lifecycle operations.

Chroma offers a direct local vector-search interface and a small development footprint. Its cost is maintaining a separate index and consistency protocol. The choice depends on search needs, scale, operational experience, and consistency requirements rather than an assumption that a dedicated vector store is always better.

### Q13. What does the singleton guarantee?

The initialization lock prevents duplicate model construction for the same cache key inside one process. It does not create one model across all worker processes or make inference concurrency unbounded.

The active API uses the shared runtime, while the standalone YouTube utility constructs its own model. Capacity planning must follow actual call paths rather than a repository-wide “singleton” label.

### Q14. What proves production readiness beyond test counts?

A credible release needs representative retrieval evaluation, real database and Redis integration coverage, security testing, concurrency measurements, and failure recovery checks. Track retrieval recall, citation consistency, answer quality, resource saturation, and end-to-end latency.

Passing unit tests proves specific invariants. Skipped integration tests and unmeasured provider behavior remain unverified; they should not be converted into a blanket zero-blocker claim.

## 7. Getting Started and Local Development

### 7.1 Prerequisites

- Python 3.11 as the tested backend baseline.
- Node.js 24 and npm for the current frontend dependencies. Node 18 is insufficient for the current Vite/Vitest toolchain.
- Docker Engine or Docker Desktop with Compose, or separately installed PostgreSQL and Redis.
- A Groq API key.
- Disk space for the Python environment, model cache, uploads, and vector index.

For a native backend, install the platform's `libmagic` and OpenMP runtime if required by the document/embedding packages. The Dockerfile installs `libmagic1` and `libgomp1`.

Commands below assume a POSIX shell and an existing local checkout. Do not copy old standalone-pipeline setup instructions into the active backend environment.

### 7.2 Install and configure the backend

From the repository root:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r backend/requirements/base.txt
python -m pip check
cd backend
cp .env.example .env
```

The base requirements include local embeddings. Optional browser-crawling dependencies are not needed for the active restricted HTTP website path.

Generate a development configuration with writable data paths and a strong secret:

```bash
python - <<'PY'
from getpass import getpass
from pathlib import Path
from secrets import token_hex
from dotenv import set_key

values = {
    "RAGFUSION_ENVIRONMENT": "development",
    "RAGFUSION_DATABASE_URL":
        "postgresql+asyncpg://docpro:docpro@127.0.0.1:55432/docpro",
    "RAGFUSION_REDIS_URL": "redis://127.0.0.1:6379/0",
    "RAGFUSION_UPLOAD_DIR": str(Path("data/uploads").resolve()),
    "RAG_VECTOR_STORE_PATH": str(Path("data/vectorstore").resolve()),
    "RAGFUSION_CORS_ORIGINS":
        '["http://localhost:5173","http://127.0.0.1:5173"]',
    "RAGFUSION_JWT_SECRET_KEY": token_hex(32),
    "RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY": "true",
    "RAGFUSION_EMBEDDING_WARMUP": "true",
    "GROQ_API_KEY": getpass("Groq API key: "),
}
for key, value in values.items():
    set_key(".env", key, value)
PY
```

Keep `.env` private. Application configuration uses `RAGFUSION_*`, RAG configuration uses `RAG_*`, and the provider key is `GROQ_API_KEY`. `RAGFUSION_DATABASE_URL` takes precedence over the compatibility alias `DATABASE_URL`.

### 7.3 Start dependencies for a host-run backend

The following local containers bind their ports only to loopback. The `docpro` password is for local development, not production.

```bash
docker run -d --name ragfusion-dev-postgres \
  -e POSTGRES_USER=docpro \
  -e POSTGRES_PASSWORD=docpro \
  -e POSTGRES_DB=docpro \
  -p 127.0.0.1:55432:5432 \
  -v ragfusion-dev-postgres:/var/lib/postgresql/data \
  postgres:16-alpine

docker run -d --name ragfusion-dev-redis \
  -p 127.0.0.1:6379:6379 \
  -v ragfusion-dev-redis:/data \
  redis:7-alpine redis-server --appendonly yes

docker exec ragfusion-dev-postgres pg_isready -U docpro -d docpro
docker exec ragfusion-dev-redis redis-cli ping
```

Reuse the containers on later starts with `docker start ragfusion-dev-postgres ragfusion-dev-redis`. Wait for database readiness before migrating.

### 7.4 Provision the model, migrate, and run

From `backend/`, with the virtual environment active, download the embedding model once:

```bash
RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=false \
python -c "from app.core.embedding_runtime import get_sentence_transformer; print(get_sentence_transformer().get_sentence_embedding_dimension())"
```

The expected dimension is `384`. Subsequent starts can use the cached model with local-only loading enabled. A custom `RAGFUSION_EMBEDDING_CACHE_DIR` must be the same during provisioning and runtime.

```bash
python -m alembic -c alembic.ini heads
python -m alembic -c alembic.ini upgrade head
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Local endpoints:

- API: `http://127.0.0.1:8000/api/v1`
- Interactive OpenAPI: `http://127.0.0.1:8000/docs`
- Schema: `http://127.0.0.1:8000/openapi.json`
- Dependency health: `http://127.0.0.1:8000/api/v1/health`

```bash
curl --fail http://127.0.0.1:8000/api/v1/health
```

Inspect the response body for `status: "ok"`, `database: true`, and `redis: true`. HTTP success alone does not prove dependency readiness or working RAG inference.

### 7.5 Run the frontend

In a second terminal, from the repository root:

```bash
cd frontend
cp .env.example .env
npm ci
npm run dev
```

The frontend configuration is:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000/api/v1
```

Open the address printed by Vite, normally `http://localhost:5173`. `VITE_*` values are browser-visible: never put signing secrets, provider keys, or database credentials in them.

### 7.6 First end-to-end check

1. Create an account and upload a small text document.
2. Wait for its ready state and confirm it appears in chat sources.
3. Ask a source-specific question and inspect the citations.
4. Add a captioned YouTube video and process a public HTML page.
5. Ask a question with several source types selected.
6. Reopen the session from history.
7. Delete the test document and confirm it is no longer selectable.

Use final website URLs that return HTML directly; redirecting URLs are deliberately rejected.

### 7.7 Docker Compose

The supplied `backend/docker-compose.yml` runs API, PostgreSQL 16, and Redis 7. It does not provide a frontend container or TLS reverse proxy. Choose this path instead of running the standalone database container on the same port.

Prepare `backend/.env` with a generated secret and Groq key as above. Compose overrides database, Redis, upload, and vector paths for the container network. Configure a persistent container model-cache location:

```bash
cd backend  # From the repository root
python - <<'PY'
from dotenv import set_key
set_key(".env", "RAGFUSION_EMBEDDING_CACHE_DIR",
        "/var/lib/ragfusion/vectorstore/model-cache")
PY

docker compose build api
docker compose up -d postgres redis
docker compose run --rm api python -m alembic -c alembic.ini upgrade head

docker compose run --rm \
  -e RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=false \
  api python -c "from app.core.embedding_runtime import get_sentence_transformer; print(get_sentence_transformer().get_sentence_embedding_dimension())"

docker compose up -d --build
docker compose logs --tail=100 api
curl --fail http://127.0.0.1:8000/api/v1/health
```

The historical Compose executable spelling is `docker-compose up -d --build`; with current Docker Compose, use `docker compose up -d --build`. Migrations and model provisioning remain required with either spelling.

The API runs as UID 10001 and exposes port 8000. PostgreSQL is available on host loopback port 55432; Redis is internal to the Compose network. Named volumes persist `postgres_data`, `redis_data`, `uploads_data`, and `vectors_data`. The model-cache command above uses a subdirectory of the vector volume.

The image does not automatically run migrations or download models at build time. Configure production credentials and network exposure before treating this development-oriented Compose stack as a production deployment.

## 8. API Guide

Application routes use `/api/v1`. Protected routes require a Bearer access token. The generated OpenAPI schema is authoritative for payload fields and validation bounds.

### Authentication and profile

- `POST /auth/signup` — create an account.
- `POST /auth/login` — obtain access and refresh tokens.
- `POST /auth/refresh` — rotate the refresh lifecycle.
- `POST /auth/logout` — revoke through the authentication version.
- `GET /auth/me` and `PATCH /auth/me` — read or edit the profile.

### Source ingestion and management

- `POST /documents/upload` — multipart document upload and processing.
- `GET /documents` and `GET /documents/{document_id}` — owned document state.
- `POST /documents/{document_id}/reprocess` — replace processed chunks and vectors.
- `DELETE /documents/{document_id}` — coordinated document deletion.
- `POST /youtube/ingest` — caption ingestion.
- `GET /youtube`, `GET /youtube/{youtube_source_id}`, and `GET /youtube/{youtube_source_id}/transcript` — source and transcript access.
- `DELETE /youtube/{youtube_source_id}` — source deletion.
- `POST /website/ingest` — register a public URL.
- `POST /website/{source_id}/process` — process its HTML content.
- `GET /website`, `GET /website/{source_id}`, and `DELETE /website/{source_id}` — owned website management.

There is no document `/status` endpoint; read the document resource to obtain its status.

### Chat, history, and settings

- `GET /chat/sources` — ready owned sources with persisted chunks.
- `POST /chat` — completed answer and citations.
- `POST /chat/stream` — SSE delivery using the current buffered implementation.
- `GET /chat/sessions` and `POST /chat/sessions` — list or create sessions.
- `GET`, `PATCH`, and `DELETE /chat/sessions/{session_id}` — load, rename, or soft-delete.
- `DELETE /chat/sessions/{session_id}/messages` — clear a session's messages.
- `/history` routes — history listing, search, and restoration.
- `GET /settings`, `PUT /settings`, and `POST /settings/reset` — stored preferences.
- `GET /dashboard` — workspace summary.
- `GET /health` and `GET /info` — dependency status and public application information.

A minimal JSON chat request is:

```json
{
  "message": "Summarize the key decisions in my indexed sources.",
  "include_sources": true
}
```

Omit `top_k`, `temperature`, and `max_tokens` to preserve saved preferences and application fallbacks. Optional `source_ids` groups document, website, and YouTube UUIDs. Those client IDs are selectors, never authorization credentials. Continuing a conversation requires its session ID.

## 9. Testing, Deployment, and Operations

### Test commands

From the repository root with the backend environment active:

```bash
RAGFUSION_EMBEDDING_WARMUP=false python -m pytest backend/tests
python -m pip check
```

Configure dedicated services for the PostgreSQL and Redis integration cases:

```bash
export BATCH2_POSTGRES_URL='postgresql+asyncpg://docpro:docpro@127.0.0.1:55432/ragfusion_test'
export BATCH3_REDIS_URL='redis://127.0.0.1:6379/15'
RAGFUSION_EMBEDDING_WARMUP=false python -m pytest backend/tests
```

Create the dedicated test database first. Never target production data. Without those services, the relevant tests skip; SQLite cannot establish PostgreSQL locking behavior.

Frontend validation and production output:

```bash
cd frontend
npm ci
npm test
npm run lint
npm run typecheck
npm run build
```

Serve `frontend/dist/` through a static host configured to fall back to `index.html` for client-side routes. Set the deployed API URL before building.

### Production release gates

- Set `RAGFUSION_ENVIRONMENT=production` and inject strong secrets outside source control.
- Replace development database credentials and restrict database/Redis network access.
- Configure exact browser origins, trusted proxies, TLS termination, and ingress body/request limits.
- Run Alembic migrations as a controlled release step.
- Provision and verify the embedding model before enabling ingestion.
- Persist and back up SQL, original files, and the complete Chroma directory.
- Run real PostgreSQL and Redis integration tests plus a deployed ingestion-to-answer smoke test.
- Measure retrieval quality and end-to-end latency using representative sources and concurrency.
- Exercise dependency failures, interrupted ingestion, and restore procedures.
- Review resolved dependencies for vulnerabilities in addition to running `pip check`.

### Operational signals

Monitor request latency by stage, `429`/`503` rates, database pool saturation, Redis failures, source processing duration, failed readiness transitions, embedding memory/CPU use, Chroma disk growth, provider errors, and file-cleanup failures.

Record retrieval counts, packed context counts, and citation identities without logging secrets or unnecessary source content. Provider token usage and client-visible latency require reliable measurement; do not infer them from character counts.

### Troubleshooting

- **Health reports Redis failure or business requests return 503:** verify Redis connectivity and credentials. Fail-closed enforcement is intentional.
- **Auth works but ingestion fails:** inspect model-cache provisioning and filesystem permissions; dependency health does not validate model readiness.
- **Website processing rejects a URL:** verify it resolves publicly, returns HTML directly, does not redirect or compress against the requested policy, and stays below 2 MiB.
- **YouTube ingestion fails:** confirm captions are accessible and an appropriate language exists; there is no automatic audio transcription fallback.
- **No citations appear:** confirm sources are ready and owned, chunks were retrieved, `include_sources` is enabled, and at least one chunk fits the context budget.
- **SSE content appears only after a delay:** this is expected for the current buffered generation path.
- **Frontend install fails on Node 18:** use Node 24 for the current dependencies.
- **Schema errors after an update:** apply the backend Alembic migrations against the intended database before restarting workers.

### Architectural follow-up work

The main remaining boundaries are direct provider-token streaming, tokenizer-aware full-prompt budgeting, durable ingestion jobs, crash reconciliation across SQL and vectors, and a measured multi-host vector deployment. These are distinct engineering tasks, not guarantees implied by the existing hardening phases.

## License

MIT is the project's stated intended license. This checkout does not currently track a root `LICENSE` file; the badge records that intent rather than linking to a nonexistent file. Include the complete license text and appropriate copyright notice before publishing a licensed release.
