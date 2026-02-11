# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A RAG (Retrieval-Augmented Generation) chatbot that answers questions about course materials. Users query through a web UI, the backend semantically searches course content stored in ChromaDB, and Claude synthesizes an answer with source attribution.

## Important

Always use `uv` to run the server, manage dependencies, and run Python files. Do not use `pip` or bare `python` directly.

## Commands

```bash
# Install dependencies
uv sync

# Run the server (from project root)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Access points
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

There are no tests, linter, or build steps configured.

## Environment Setup

Requires a `.env` file in the project root with `ANTHROPIC_API_KEY=<key>`. The `.env.example` file has the template.

## Architecture

### Query Flow

Frontend (`frontend/script.js`) → FastAPI (`backend/app.py`) → `RAGSystem` → `AIGenerator` → Claude API. Claude has access to a `search_course_content` tool. If Claude invokes it, the tool executes a semantic search against ChromaDB, results are fed back, and Claude makes a second API call to synthesize the final answer. If Claude doesn't invoke the tool, the first response is returned directly.

### Key Components (all in `backend/`)

- **RAGSystem** (`rag_system.py`): Orchestrator that wires all components together. Entry point is `query()`.
- **AIGenerator** (`ai_generator.py`): Wraps Anthropic SDK. Handles the tool-use loop: first call with tools → execute tool → second call without tools to synthesize. System prompt is a static class attribute `SYSTEM_PROMPT`.
- **VectorStore** (`vector_store.py`): ChromaDB wrapper with two collections: `course_catalog` (course metadata for fuzzy name resolution) and `course_content` (chunked text for semantic search). Uses `all-MiniLM-L6-v2` sentence-transformer embeddings.
- **DocumentProcessor** (`document_processor.py`): Parses structured course documents (title/link/instructor header, then `Lesson N:` markers), chunks text by sentence boundaries (800 chars, 100 overlap).
- **ToolManager / CourseSearchTool** (`search_tools.py`): Implements Anthropic tool-calling interface. `CourseSearchTool` resolves fuzzy course names via catalog search, then queries content collection. Tracks `last_sources` for the response.
- **SessionManager** (`session_manager.py`): In-memory conversation history per session. History is formatted as a string and appended to the system prompt (not as separate messages). Capped at 2 exchanges.

### Frontend

Vanilla HTML/CSS/JS in `frontend/`. No build step. Served as static files by FastAPI. Uses `marked.js` (CDN) for markdown rendering.

### Course Documents

Plain text files in `docs/` with a specific format: metadata header (Course Title/Link/Instructor), then `Lesson N: Title` markers followed by content. Loaded automatically on server startup. ChromaDB persists to `backend/chroma_db/` — documents are only re-processed if their title doesn't already exist in the store.

### Data Models (`models.py`)

Pydantic models: `Course` (title as unique ID, lessons list), `Lesson` (number, title, link), `CourseChunk` (content, course_title, lesson_number, chunk_index).

## Configuration

All config is in `backend/config.py` as a dataclass. Key values: model `claude-sonnet-4-20250514`, chunk size 800, overlap 100, max search results 5, max conversation history 2 exchanges. ChromaDB path is `./chroma_db` (relative to `backend/`).
