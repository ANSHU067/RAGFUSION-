"""Configuration settings for the RAG pipeline."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Model Configuration
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4")

# Vector Store Configuration
VECTOR_STORE_PATH = Path(os.getenv("VECTOR_STORE_PATH", "./data/vectorstore"))
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)

# Retrieval Configuration
TOP_K_RETRIEVAL = 10  # Number of documents to retrieve initially
TOP_K_RERANK = 5      # Number of documents after reranking

# Embedding Configuration
EMBEDDING_DIMENSION = 1536  # For text-embedding-3-small
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# LLM Configuration
TEMPERATURE = 0.0
MAX_TOKENS = 1000

# Reranking Configuration
RERANK_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
