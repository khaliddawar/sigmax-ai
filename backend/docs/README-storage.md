# BPT Storage Options

## Overview

The BPT (Big Picture Trading) system supports two storage options for transcripts and related data:

1. **Supabase with pgvector** (Primary)
2. **Local File Storage** (Fallback)

This document explains how to use each option and when to choose one over the other.

## Supabase Storage (Primary)

Supabase with pgvector is the primary storage option, offering advanced vector search capabilities for efficient similarity search of transcript chunks.

### Requirements:
- Supabase project setup with pgvector extension enabled
- `SUPABASE_URL` and `SUPABASE_KEY` environment variables configured

### Advantages:
- Efficient vector similarity search for Q&A functionality
- Remote database accessible from multiple instances
- Scalable for large numbers of transcripts
- Supports Row Level Security for advanced permissions

### Setup:
1. Create a Supabase project at [supabase.com](https://supabase.com)
2. Enable the pgvector extension
3. Run the setup SQL scripts for tables and functions
4. Configure environment variables:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-key
   ```

## File Storage (Fallback)

The file storage option provides a simple, zero-configuration alternative that stores all data as JSON files in a local directory structure.

### Requirements:
- No external dependencies
- No environment variables required
- Writable filesystem

### Advantages:
- Zero configuration - works out of the box
- No external dependencies
- Easy to inspect data (simple JSON files)
- Portable - entire dataset in a directory structure

### Structure:
- `data/transcripts/` - Transcript metadata as JSON files
- `data/chunks/{transcript_id}/` - Transcript chunks as JSON files
- `data/embeddings/{transcript_id}/` - Vector embeddings as JSON files
- `data/trades/{transcript_id}/` - Extracted trades as JSON files

### Limitations:
- No vector similarity search (falls back to keyword search)
- Limited to local file system
- Not suitable for production with multiple instances
- Less efficient for large datasets

## Switching Between Storage Options

The system automatically selects the appropriate storage method based on environment variables:

1. **Use Supabase**:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-key
   ```

2. **Force File Storage**:
   - Either don't set the Supabase environment variables
   - Or use the `--file-storage` flag:
     ```
     python run_with_ingestion.py --file-storage
     ```
     ```
     python scripts/test_ingestion_pipeline.py --file-storage
     ```

## When to Use Each Option

- **Use Supabase** for:
  - Production deployments
  - Multi-user systems
  - Advanced vector search capabilities
  - Large numbers of transcripts

- **Use File Storage** for:
  - Quick prototyping
  - Local development
  - Offline usage
  - Simple testing
  - When you don't have Supabase configured yet

## Using Both in Development

A common development pattern is to:

1. Start with file storage for quick initial development
2. Set up Supabase when vector search capabilities are needed
3. Keep file storage as a fallback for offline development or testing

## Search Capabilities

The storage option affects search capabilities:

1. **With Supabase**: Vector similarity search for accurate retrieval
2. **With File Storage**: Keyword-based search that extracts important terms from queries

## Recommendations

For optimal results:

1. **Development**: Use file storage for initial development until Supabase is needed
2. **Testing**: Use the `--file-storage` flag with test scripts for isolated testing
3. **Production**: Configure Supabase for advanced features and scalability 