FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    HF_HOME=/app/cache/huggingface \
    RAGFUSION_EMBEDDING_CACHE_DIR=/app/cache/fastembed \
    RAGFUSION_EMBEDDING_LOCAL_FILES_ONLY=false \
    RAGFUSION_EMBEDDING_WARMUP=false \
    RAGFUSION_UPLOAD_DIR=/app/uploads \
    RAG_VECTOR_STORE_PATH=/app/data/vectorstore \
    RAGFUSION_ENVIRONMENT=production \
    TOKENIZERS_PARALLELISM=false \
    UNSTRUCTURED_DISABLE_NOTICE=1 \
    OMP_NUM_THREADS=1 \
    OPENBLAS_NUM_THREADS=1

RUN groupadd --gid 1000 user \
    && useradd --uid 1000 --gid 1000 --create-home user \
    && mkdir -p /app/data /app/uploads /app/cache \
    && chown -R 1000:1000 /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libmagic1 libgomp1 curl build-essential \
    && rm -rf /var/lib/apt/lists/*

# Build context is backend/: preserve the nested -r embeddings.txt include.
COPY --chown=1000:1000 requirements/ /app/requirements/
USER 1000:1000
RUN python -m pip install --user --no-cache-dir --upgrade pip \
    && python -m pip install --user --no-cache-dir -r /app/requirements/base.txt \
    && python -m pip check \
    && python -c "from importlib.util import find_spec; assert not any(find_spec(name) for name in ('torch', 'torchvision', 'sentence_transformers', 'transformers', 'FlagEmbedding')), 'Heavy embedding dependency reintroduced'"

# Download at build time, then verify the same cache loads without networking.
RUN python -c "import os; from fastembed import TextEmbedding; name = 'sentence-transformers/all-MiniLM-L6-v2'; cache = os.environ['RAGFUSION_EMBEDDING_CACHE_DIR']; TextEmbedding(model_name=name, cache_dir=cache, threads=1); model = TextEmbedding(model_name=name, cache_dir=cache, threads=1, local_files_only=True); assert len(next(model.embed(['cache verification'], batch_size=1))) == 384"

# The existing Unstructured parser also needs language data. Install it into
# the user's site-packages at build time, not into a read-only runtime prefix.
RUN python -m pip install --user --no-cache-dir \
    "https://github.com/explosion/spacy-models/releases/download/en_core_web_sm-3.8.0/en_core_web_sm-3.8.0-py3-none-any.whl#sha256=1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85" \
    && python -m pip check

COPY --chown=1000:1000 . /app/
RUN chmod 755 /app/entrypoint.sh

EXPOSE 7860

ENTRYPOINT ["/app/entrypoint.sh"]
