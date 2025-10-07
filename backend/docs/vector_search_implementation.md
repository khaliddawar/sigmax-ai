# Vector Search Implementation

This document describes the vector search implementation in the BPT (Big Picture Trading) application.

## Overview

Vector search enables the application to find the most semantically relevant text chunks from meeting transcripts to answer user questions. Unlike pattern matching or keyword search, vector search uses the meaning of the text to identify the most relevant content.

## Implementation Components

The vector search implementation consists of the following components:

1. **Embedding Service (`app/services/embedding_service.py`)**:
   - Converts text into numerical vector representations (embeddings)
   - Supports OpenAI's text-embedding-ada-002 model
   - Includes fallback to mock embeddings if API calls fail

2. **Supabase Service (`app/services/supabase_client.py`)**:
   - Handles database operations for transcript storage
   - Supports pgvector extension for vector similarity search
   - Includes methods for storing and retrieving embeddings
   - Provides similarity search functionality

3. **Retrieval QA Service (`app/services/retrieval_qa_service.py`)**:
   - Orchestrates the question-answering process
   - Retrieves relevant chunks using vector similarity
   - Constructs context from retrieved chunks
   - Generates answers using LLM API
   - Supports multiple LLM providers (OpenAI, Anthropic, Azure, etc.)

4. **API Endpoint (`simple_fastapi.py`)**:
   - Exposes QA functionality through `/api/qa` endpoint
   - Processes user questions and returns answers
   - Falls back to pattern matching if vector search fails

## Data Flow

1. User sends a question to the `/api/qa` endpoint
2. The question is converted to an embedding vector
3. The embedding is used to find similar chunks in the database
4. Retrieved chunks are ranked by similarity
5. Top chunks are assembled into a context
6. The context and question are sent to the LLM to generate an answer
7. The answer, sources, and metadata are returned to the user

## Configuration

Vector search can be configured using the following environment variables:

- `OPENAI_API_KEY`: API key for embedding generation
- `QA_MODEL`: Model to use for answer generation (e.g., "gpt-4o-mini")
- `USE_MOCK_EMBEDDINGS`: Set to "true" to use mock embeddings instead of calling the API
- `USE_MOCK_RESPONSES`: Set to "true" to use mock responses for QA service
- `MAX_CONTEXT_LENGTH`: Maximum length of context to send to the LLM

## Setup Requirements

To use vector search, you need:

1. **Supabase Project** with:
   - pgvector extension enabled
   - Correct database tables and functions set up
   - Proper permissions configured

2. **API Keys** for:
   - OpenAI API (for embeddings)
   - LLM provider of your choice (OpenAI, Anthropic, Azure, etc.)

## Testing

The implementation includes comprehensive testing:

1. **Unit Tests** (`tests/test_pgvector.py`):
   - Test pgvector setup and integration
   - Test storing and retrieving embeddings
   - Test similarity search

2. **End-to-End Tests** (`tests/test_vector_search.py`):
   - Test the complete vector search pipeline
   - Test the API endpoint
   - Support for mock data to avoid API dependencies

## Fallback Mechanisms

The implementation includes multiple fallback mechanisms:

1. If embedding generation fails, it falls back to mock embeddings
2. If vector search fails, it falls back to pattern matching
3. If the LLM API fails, it falls back to mock responses

## Future Improvements

Potential improvements for the vector search implementation:

1. **Hybrid Search**: Combine vector search with keyword search for better results
2. **Chunking Optimization**: Implement more sophisticated chunking strategies
3. **Embedding Caching**: Cache embeddings to reduce API calls
4. **Multiple Embedding Models**: Support different embedding models
5. **Query Refinement**: Pre-process questions to improve search results 