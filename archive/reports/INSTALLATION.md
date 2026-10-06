# RAG Pipeline - Installation Guide

## Prerequisites

- Python 3.8 or higher
- pip package manager
- OpenAI API key

## Installation Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- LangChain & LangGraph (RAG framework)
- ChromaDB (vector database)
- OpenAI SDK (embeddings & LLM)
- Sentence Transformers (reranking)
- pytest (testing)

### 2. Configure Environment

```bash
# Copy the example environment file
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-key-here
```

### 3. Verify Installation

Run the quickstart script:

```bash
python quickstart.py
```

This will:
- ✅ Check environment setup
- ✅ Test all imports
- ✅ Run a simple RAG demo
- ✅ Verify everything works

## Quick Test

```bash
# Run all tests
pytest tests/ -v

# Run specific tests
pytest tests/test_retrieval_accuracy.py -v -s
```

## What Gets Installed

### Core Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| langchain | ≥0.1.0 | LLM framework |
| langgraph | ≥0.0.20 | Workflow orchestration |
| langchain-openai | ≥0.0.5 | OpenAI integration |
| chromadb | ≥0.4.22 | Vector database |
| sentence-transformers | ≥2.2.2 | Reranking models |
| openai | ≥1.12.0 | OpenAI API |
| faiss-cpu | ≥1.7.4 | Vector search |

### Testing & Development

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | ≥7.4.0 | Testing framework |
| pytest-asyncio | ≥0.21.0 | Async testing |
| python-dotenv | ≥1.0.0 | Environment management |

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'langchain'`

**Solution**:
```bash
pip install -r requirements.txt
```

### API Key Issues

**Problem**: `ValueError: OpenAI API key is required`

**Solution**:
1. Create `.env` file: `cp .env.example .env`
2. Add your key: `OPENAI_API_KEY=sk-your-key-here`

### Vector Store Errors

**Problem**: `Cannot write to vector store directory`

**Solution**:
```bash
# Create directory with proper permissions
mkdir -p ./data/vectorstore
chmod 755 ./data/vectorstore
```

### ChromaDB Issues

**Problem**: `ChromaDB connection errors`

**Solution**:
```bash
# Remove old ChromaDB files
rm -rf ./data/vectorstore/chroma.sqlite3

# Reinstall ChromaDB
pip install --upgrade chromadb
```

## Platform-Specific Notes

### macOS

```bash
# May need to install additional dependencies
brew install python@3.11
pip3 install -r requirements.txt
```

### Linux

```bash
# Install system dependencies
sudo apt-get update
sudo apt-get install python3-dev build-essential

pip install -r requirements.txt
```

### Windows

```bash
# Use Python launcher
py -m pip install -r requirements.txt

# Set environment variable
set OPENAI_API_KEY=sk-your-key-here
```

## GPU Support (Optional)

For faster embedding generation:

```bash
# Install PyTorch with CUDA support
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Update sentence-transformers
pip install --upgrade sentence-transformers
```

## Verification Checklist

After installation, verify:

- [ ] Python version ≥ 3.8
- [ ] All packages installed
- [ ] `.env` file created
- [ ] OpenAI API key set
- [ ] `quickstart.py` runs successfully
- [ ] Tests pass: `pytest tests/ -v`

## Next Steps

1. ✅ **Run examples**: `python examples.py`
2. ✅ **Read documentation**: `RAG_PIPELINE_README.md`
3. ✅ **Run tests**: `pytest tests/ -v -s`
4. ✅ **Customize config**: Edit `config.py`

## Getting Help

- Check `RAG_PIPELINE_README.md` for usage documentation
- See `PROJECT_SUMMARY.md` for architecture overview
- Review `examples.py` for code samples
- Run tests to verify functionality

