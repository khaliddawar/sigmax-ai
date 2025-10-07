# Supabase pgvector Integration

This document provides instructions for setting up and using pgvector in your Supabase PostgreSQL database for the BPT application.

## 1. Requirements

Before proceeding, make sure you have:

- A Supabase project
- Admin access to enable extensions
- The following environment variables set in your `.env` file:
  ```
  # Supabase configuration
  SUPABASE_URL=https://your-project-id.supabase.co
  SUPABASE_KEY=your_supabase_anon_key
  
  # OpenAI API key for embeddings and QA
  OPENAI_API_KEY=your_openai_api_key
  ```

## 2. Setting Up Supabase for pgvector

Follow these steps in order:

### Step 1: Install Helper Functions

First, install the helper functions that allow the application to check and manage extensions:

1. Log in to your Supabase dashboard at [app.supabase.com](https://app.supabase.com)
2. Select your project
3. Navigate to the SQL Editor
4. Create a new query
5. Copy and paste the contents of `scripts/install_helper_functions.sql`
6. Run the query

These functions provide:
- `check_extension_exists(extension_name)`: Safely checks if an extension is installed
- `exec_sql(sql)`: Allows executing SQL from the application (service role only)

### Step 2: Enable pgvector Extension

After installing the helper functions, enable the pgvector extension:

1. In the same SQL Editor, run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. Alternatively, use the API endpoint:
   ```
   POST /api/setup/pgvector
   ```

### Step 3: Create Schema and Tables

Create the necessary tables for storing embeddings:

1. In the SQL Editor, run the contents of `scripts/supabase_setup.sql`, or
2. Use the API to run the setup script

## 3. Verifying the Setup

To verify that pgvector is properly set up:

1. Check the pgvector status using the API endpoint:
   ```
   GET /api/check/pgvector
   ```

2. The response should indicate that pgvector is enabled:
   ```json
   {
     "success": true,
     "is_enabled": true
   }
   ```

3. You can also check directly in the SQL Editor:
   ```sql
   SELECT * FROM pg_extension WHERE extname = 'vector';
   ```

## 4. Using pgvector in the Application

The application uses pgvector through the `SupabaseService` class, which provides:

- `check_pgvector()`: Checks if pgvector is installed
- `setup_pgvector()`: Installs pgvector and creates necessary tables
- `store_transcript_chunks()`: Stores transcript chunks in the database
- `store_embeddings()`: Stores vector embeddings for transcript chunks
- `create_transcript_with_embeddings()`: Combined method to store a transcript with embeddings
- `search_similar_chunks()`: Searches for chunks similar to a query using vector similarity

## 5. Troubleshooting

### Missing Helper Functions

If you see errors like:
```
Could not find the function public.check_extension_exists(extension_name) in the schema cache
```
or
```
Could not find the function public.exec_sql(sql) in the schema cache
```

**Solution:**
Run the helper functions installation script as described in Step 1 above.

### Connection Issues

If you see:
```
Failed to initialize Supabase client
```

**Solutions:**
1. Verify that your Supabase URL and key are correct in the `.env` file
2. Make sure you're using the anon key (public key) for client-side access
3. Verify that your Supabase instance is running

### Vector Extension Not Found

If you see:
```
pgvector extension is not installed
```

**Solution:**
Run the pgvector setup process as described in Step 2.

## 6. Performance Optimization

For production environments with large datasets, consider these optimizations:

1. Adjust the IVFFlat index parameters:
   ```sql
   -- Recreate the index with more lists for larger datasets
   DROP INDEX IF EXISTS transcript_chunks_embedding_idx;
   CREATE INDEX transcript_chunks_embedding_idx ON transcript_chunks 
   USING ivfflat (embedding vector_cosine_ops) WITH (lists = 500);
   ```

2. Consider using a smaller embedding dimension:
   - OpenAI Ada 002 (1536 dimensions)
   - or local models with smaller dimensions (e.g., 384 dimensions)

3. Add task-specific indexes:
   ```sql
   CREATE INDEX idx_transcript_chunks_transcript_id ON transcript_chunks(transcript_id);
   ```

---

See the full implementation in `app/services/supabase_client.py` for more details. 