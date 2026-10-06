# Phase 8 & 9 Recovery Inventory
## Generated: August 2, 2026

---

## CURRENT SITUATION ANALYSIS

### Root-Level Files That Need Migration

#### Phase 8 RAG Components (Misplaced in Root)
```
/config.py                  → backend/app/core/rag_config.py
/embedding.py               → backend/app/rag/embeddings/embedding_manager.py
/retrieval.py               → backend/app/rag/retrievers/retriever_manager.py
/reranking.py               → backend/app/rag/rerankers/reranker_manager.py
/prompt_creation.py         → backend/app/rag/prompts/prompt_builder.py
/rag_pipeline.py            → backend/app/rag/pipelines/rag_pipeline.py
```

#### Test Files (Misplaced in Root)
```
/tests/                     → backend/tests/rag/
/tests/__init__.py
/tests/conftest.py
/tests/test_retrieval_accuracy.py
/tests/test_hallucination.py
/tests/test_context_injection.py
/tests/test_pipeline.py
/tests/test_vector_store.py
```

#### Standalone Test Scripts (Should Be in backend/tests/)
```
/test_vector_store_manual.py
/test_vector_store_standalone.py
/test_vector_store_simple.py
```

#### Example Scripts (Should Be in examples/)
```
/examples.py                → examples/rag_examples.py
/quickstart.py              → examples/quickstart.py
/examples/demo.py           (already in correct location)
/examples/embedding_examples.py (already in correct location)
```

#### Documentation Files (Keep in Root, Review for Updates)
```
/PROJECT_SUMMARY.md
/RAG_PIPELINE_README.md
/EMBEDDING_IMPLEMENTATION.md
/EMBEDDING_QUICKSTART.txt
/VECTOR_STORE_README.md
/WEBSITE_INGESTION_COMPLETION_REPORT.md
/BACKEND_AUDIT_REPORT.md
/FIXES_APPLIED.md
/INSTALLATION.md
/README.md
/BACKEND.md
/FRONTEND.md
/TODOO.md
```

#### Verification Scripts (Should Be in backend/scripts/)
```
/backend/verify_embedding_service.py     → backend/scripts/verify_embedding.py
/backend/verify_embedding_standalone.py  → backend/scripts/verify_standalone.py
/SETUP.py                                → backend/scripts/setup.py
/quick_test.py                           → backend/scripts/quick_test.py
```

---

## EXISTING BACKEND STRUCTURE

### Current backend/app/ Directories
```
backend/app/
├── __init__.py
├── api/                 ✓ Routes layer
├── config/              ✓ Configuration
├── core/                ✓ Core utilities
├── db/                  ✓ Database layer
├── dependencies/        ✓ Dependency injection
├── middleware/          ✓ Middleware
├── models/              ✓ SQLAlchemy models
├── repositories/        ✓ Data access layer
├── schemas/             ✓ Pydantic schemas
├── services/            ✓ Business logic
├── utils/               ✓ Utilities
└── workers/             ✓ Background tasks
```

### Missing Directories (Phase 8 & 9)
```
backend/app/rag/         ✗ RAG components (Phase 8)
backend/app/llm/         ✗ LLM components (Phase 9)
```

---

## REQUIRED DIRECTORY STRUCTURE

### Phase 8: RAG Architecture
```
backend/app/rag/
├── __init__.py
├── embeddings/
│   ├── __init__.py
│   └── embedding_manager.py      (from /embedding.py)
├── retrievers/
│   ├── __init__.py
│   ├── retriever_manager.py      (from /retrieval.py)
│   ├── hybrid_retriever.py       (new)
│   └── metadata_filter.py        (new)
├── rerankers/
│   ├── __init__.py
│   ├── reranker_manager.py       (from /reranking.py)
│   └── hybrid_reranker.py        (extract from /reranking.py)
├── pipelines/
│   ├── __init__.py
│   ├── rag_pipeline.py           (from /rag_pipeline.py)
│   └── pipeline_state.py         (new)
├── prompts/
│   ├── __init__.py
│   ├── prompt_builder.py         (from /prompt_creation.py)
│   └── templates.py              (extract from /prompt_creation.py)
├── cache/
│   ├── __init__.py
│   └── redis_cache.py            (new integration with Redis)
├── filters/
│   ├── __init__.py
│   └── metadata_filter.py        (new)
├── memory/
│   ├── __init__.py
│   └── conversation_memory.py    (new)
└── utils/
    ├── __init__.py
    └── text_processing.py        (new)
```

### Phase 9: LLM Architecture
```
backend/app/llm/
├── __init__.py
├── providers/
│   ├── __init__.py
│   ├── base.py                   (new - abstract base)
│   ├── openai_provider.py        (new)
│   ├── anthropic_provider.py     (new)
│   ├── gemini_provider.py        (new)
│   ├── groq_provider.py          (new)
│   ├── openrouter_provider.py    (new)
│   └── ollama_provider.py        (new)
├── streaming/
│   ├── __init__.py
│   └── stream_handler.py         (new)
├── callbacks/
│   ├── __init__.py
│   ├── token_counter.py          (new)
│   └── logger_callback.py        (new)
├── prompts/
│   ├── __init__.py
│   └── system_prompts.py         (new)
├── parsers/
│   ├── __init__.py
│   └── output_parser.py          (new)
├── tokenizers/
│   ├── __init__.py
│   └── token_counter.py          (new)
├── models/
│   ├── __init__.py
│   └── model_config.py           (new)
└── utils/
    ├── __init__.py
    ├── retry_logic.py            (new)
    └── fallback_handler.py       (new)
```

---

## EXISTING SERVICE INTEGRATIONS

### Current Services That Interact With RAG/LLM
```
backend/app/services/
├── embedding_service.py          (existing - needs integration)
├── embedding_cache.py            (existing - needs integration)
├── embedding_helper.py           (existing - needs integration)
├── embedding_integration.py      (existing - needs integration)
├── chunking_service.py           (existing - needs integration)
├── extraction_service.py         (existing - needs integration)
├── ingestion_service.py          (existing - needs integration)
└── document.py                   (existing - needs integration)
```

### Integration Required
- Connect `embedding_service.py` → `backend/app/rag/embeddings/`
- Connect `chunking_service.py` → `backend/app/rag/utils/`
- Route RAG pipeline through proper service layer

---

## DUPLICATE FILES TO RESOLVE

### Vector Store Implementations
```
/backend/app/db/vector_store.py   (existing in backend)
/tests/test_vector_store.py       (root tests)
/test_vector_store_manual.py      (root standalone)
/test_vector_store_standalone.py  (root standalone)
/test_vector_store_simple.py      (root standalone)
```
**Resolution**: Keep backend implementation, migrate tests properly

### Config Files
```
/config.py                        (root - RAG config)
/backend/app/config/settings.py   (existing - main config)
/backend/app/config/embedding_config.py (existing - embedding config)
```
**Resolution**: Merge RAG config into backend structure

### Test Directories
```
/tests/                           (root)
/backend/tests/                   (proper location)
```
**Resolution**: Migrate root tests to backend/tests/rag/

---

## IMPORT DEPENDENCIES TO FIX

### Current Imports in Root Files
```python
# These imports will break after migration:
from config import OPENAI_API_KEY, EMBEDDING_MODEL
from embedding import EmbeddingManager
from retrieval import RetrieverManager
from reranking import RerankerManager
from prompt_creation import PromptBuilder
```

### Required New Imports
```python
# After migration:
from app.core.rag_config import get_rag_config
from app.rag.embeddings.embedding_manager import EmbeddingManager
from app.rag.retrievers.retriever_manager import RetrieverManager
from app.rag.rerankers.reranker_manager import RerankerManager
from app.rag.prompts.prompt_builder import PromptBuilder
from app.rag.pipelines.rag_pipeline import RAGPipeline
```

---

## EXTERNAL DEPENDENCIES

### Root-Level Dependencies (from root files)
```
langchain
langchain-openai
langchain-community
langgraph
chromadb
sentence-transformers
python-dotenv
```

### Should Already Be In requirements.txt
Check and verify all Phase 8 & 9 dependencies are included

---

## YOUTUBE PIPELINE (Separate Module)
```
/youtube_pipeline/
├── __init__.py
├── transcript_extractor.py
├── metadata_extractor.py
├── chunker.py
├── embedding_generator.py
└── pipeline.py
```

**Status**: Keep separate for now, integrate later through services
**Action**: Create bridge service in `backend/app/services/youtube_service.py`

---

## MIGRATION PRIORITY ORDER

### Priority 1: Create Directory Structure
1. Create `backend/app/rag/` with all subdirectories
2. Create `backend/app/llm/` with all subdirectories

### Priority 2: Migrate Core RAG Components
1. Move and adapt `/config.py` → `backend/app/core/rag_config.py`
2. Move and adapt `/embedding.py` → `backend/app/rag/embeddings/`
3. Move and adapt `/retrieval.py` → `backend/app/rag/retrievers/`
4. Move and adapt `/reranking.py` → `backend/app/rag/rerankers/`
5. Move and adapt `/prompt_creation.py` → `backend/app/rag/prompts/`
6. Move and adapt `/rag_pipeline.py` → `backend/app/rag/pipelines/`

### Priority 3: Fix All Imports
1. Update internal imports in migrated files
2. Update imports in existing services
3. Update imports in tests

### Priority 4: Migrate Tests
1. Create `backend/tests/rag/`
2. Move `/tests/test_*.py` → `backend/tests/rag/`
3. Update test imports
4. Consolidate duplicate test files

### Priority 5: Migrate Examples and Scripts
1. Move examples to proper location
2. Move verification scripts to `backend/scripts/`
3. Update their imports

### Priority 6: Create Phase 9 Stubs
1. Create LLM provider base classes
2. Create placeholder implementations
3. Document Phase 9 architecture

### Priority 7: Integration Layer
1. Create service bridges
2. Update API endpoints
3. Wire up dependency injection

### Priority 8: Cleanup
1. Archive obsolete files
2. Remove duplicates
3. Update documentation

---

## FILES TO ARCHIVE (Not Delete)
```
Create: /archive/phase8-9-recovery/
Move these for reference:
- All root-level .py files after successful migration
- Duplicate test files after consolidation
- Old documentation after updates
```

---

## VALIDATION CHECKLIST

### After Migration
- [ ] All imports resolve correctly
- [ ] No circular dependencies
- [ ] Tests pass
- [ ] Services integrate properly
- [ ] API endpoints work
- [ ] Documentation updated
- [ ] No duplicate implementations
- [ ] No files in wrong locations

---

## NEXT STEPS

1. **Create directory structure** for Phase 8 and Phase 9
2. **Migrate config.py** first (needed by all other components)
3. **Migrate embedding.py** (base dependency)
4. **Migrate retrieval.py** (depends on embedding)
5. **Migrate reranking.py** (depends on retrieval)
6. **Migrate prompt_creation.py** (independent)
7. **Migrate rag_pipeline.py** (depends on all above)
8. **Fix all imports systematically**
9. **Migrate and fix tests**
10. **Create Phase 9 structure** (LLM providers)
11. **Validate and test**
12. **Generate reports**

---

## RISK AREAS

### High Risk
- Circular import dependencies
- Config management conflicts
- Existing service integration breaking
- Database session handling in new structure

### Medium Risk
- Test fixtures compatibility
- Example scripts breaking
- Documentation becoming outdated

### Low Risk
- Archive file organization
- Comment/docstring updates

---

## END OF INVENTORY
