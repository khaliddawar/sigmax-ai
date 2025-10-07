# Supabase Setup Guide - YouTube Extension

## Overview

The YouTube Extension has been successfully integrated with the existing BPT (Bullish/Bearish/Pullback Trader) Supabase project. This approach provides:

- **Shared Infrastructure**: Leverages existing transcripts, semantic chunks, and chat functionality
- **Cost Efficiency**: No need for a separate Supabase project
- **Unified Data**: YouTube transcripts can benefit from existing BPT analysis capabilities

## Project Details

**Project Name**: BPT Pipeline System  
**Project ID**: `hohpifdmvnwasmrmxonh`  
**Project URL**: `https://hohpifdmvnwasmrmxonh.supabase.co`  
**Region**: `us-west-1`

## Database Schema

### New Tables Added for YouTube Extension

#### 1. `user_profiles`
- **Purpose**: User management with quota limits
- **Key Fields**:
  - `user_id` (UUID) - References auth.users
  - `email` (TEXT) - User email
  - `plan_type` (TEXT) - 'free', 'premium', 'enterprise'
  - `plan_limits` (JSONB) - Quota configuration
  - `subscription_status` (TEXT) - 'active', 'cancelled', 'expired'

#### 2. `usage_ledger`
- **Purpose**: Track quota consumption
- **Key Fields**:
  - `user_id` (UUID) - User identifier
  - `resource_type` (TEXT) - 'tokens', 'requests', etc.
  - `amount` (NUMBER) - Amount consumed
  - `metadata` (JSONB) - Additional context

#### 3. `youtube_videos`
- **Purpose**: YouTube-specific metadata
- **Key Fields**:
  - `video_id` (TEXT) - YouTube video ID
  - `video_url` (TEXT) - Full YouTube URL
  - `transcript_id` (TEXT) - Links to transcripts table
  - `channel_name`, `thumbnail_url`, etc. - Rich metadata

### Existing Tables (Inherited from BPT)

- **`transcripts`** - Main transcript storage (supports YouTube via `source` field)
- **`semantic_chunks`** - Semantic chunking with pgvector embeddings
- **`chat_sessions`** & **`chat_messages`** - RAG chat functionality
- **`trade_ideas`** & **`trades`** - Financial analysis (can work with YouTube content)

## Database Functions

### Quota Management Functions

1. **`get_user_quota_limits(user_id)`**
   - Returns user's quota limits
   - Falls back to default limits if user not found

2. **`check_user_quota(user_id, resource_type, amount)`**
   - Checks if user can consume specified quota
   - Returns boolean

3. **`consume_user_quota(user_id, resource_type, amount, metadata)`**
   - Consumes quota and logs to usage_ledger
   - Returns boolean success

4. **`get_user_quota_usage(user_id)`**
   - Returns current usage statistics
   - Includes daily and monthly consumption

### Vector Search Functions (Inherited)

- `match_semantic_chunks()` - Semantic search across all transcripts
- `match_transcript_semantic_chunks()` - Search within specific transcript
- `match_chunks_by_entities()` - Entity-based filtering

## Row Level Security (RLS)

All new tables have RLS enabled with policies:

- **user_profiles**: Users can only access their own profile
- **usage_ledger**: Users can view their own usage, system can insert
- **youtube_videos**: Users can view videos they processed

## Configuration

### Backend Environment Variables

```bash
# Supabase Configuration
SUPABASE_URL=https://hohpifdmvnwasmrmxonh.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvaHBpZmRtdm53YXNtcm14b25oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDczOTYxMjMsImV4cCI6MjA2Mjk3MjEyM30.8YVMTs3vAzsXeimGARTg5kNx1fBzguS5igvpW-jaIyo
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key_here
```

### Extension MCP Configuration

Add to `.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "supabase": {
      "command": "npx",
      "args": ["@supabase/mcp-server"],
      "env": {
        "SUPABASE_URL": "https://hohpifdmvnwasmrmxonh.supabase.co",
        "SUPABASE_ANON_KEY": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImhvaHBpZmRtdm53YXNtcm14b25oIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDczOTYxMjMsImV4cCI6MjA2Mjk3MjEyM30.8YVMTs3vAzsXeimGARTg5kNx1fBzguS5igvpW-jaIyo"
      }
    }
  }
}
```

## Default Quota Limits

### Free Plan
```json
{
  "monthly_tokens": 50000,
  "daily_requests": 100,
  "max_video_duration": 3600,
  "concurrent_jobs": 2,
  "email_summaries": true,
  "priority_processing": false
}
```

### Premium Plan (Future)
```json
{
  "monthly_tokens": 200000,
  "daily_requests": 500,
  "max_video_duration": 7200,
  "concurrent_jobs": 5,
  "email_summaries": true,
  "priority_processing": true
}
```

## Testing the Setup

### 1. Test Quota Functions
```sql
-- Test default limits
SELECT get_user_quota_limits('test-user-id'::uuid);

-- Test quota checking
SELECT check_user_quota('test-user-id'::uuid, 'tokens', 1000);

-- Test quota consumption
SELECT consume_user_quota('test-user-id'::uuid, 'tokens', 1000, '{"video_id": "test123"}'::jsonb);
```

### 2. Test Vector Search
```sql
-- Test semantic search (requires embeddings)
SELECT * FROM match_semantic_chunks('[embedding_vector]', 0.7, 5);
```

### 3. Test User Profile Creation
```sql
-- This requires a valid auth.users entry first
INSERT INTO user_profiles (user_id, email, full_name)
VALUES ('valid-auth-user-id'::uuid, 'user@example.com', 'Test User');
```

## Migration History

1. **`add_youtube_extension_support`** - Added user_profiles, usage_ledger, youtube_videos tables
2. **`add_quota_management_functions`** - Added quota management SQL functions
3. **`enable_rls_youtube_extension`** - Enabled Row Level Security policies

## Next Steps

1. **Get Service Role Key**: Contact Supabase project admin for service role key
2. **Set up Authentication**: Configure Supabase Auth for extension users
3. **Test Integration**: Verify backend can connect and perform operations
4. **Monitor Usage**: Set up monitoring for quota consumption

## Troubleshooting

### Common Issues

1. **Foreign Key Violations**: Ensure users exist in auth.users before creating profiles
2. **RLS Policies**: Make sure user is authenticated when accessing user-specific data
3. **Quota Limits**: Check quota functions return expected default values

### Useful Queries

```sql
-- Check table structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'user_profiles';

-- Check RLS policies
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual 
FROM pg_policies 
WHERE tablename IN ('user_profiles', 'usage_ledger', 'youtube_videos');

-- Check current usage for a user
SELECT resource_type, SUM(amount) as total_used
FROM usage_ledger 
WHERE user_id = 'test-user-id'::uuid 
GROUP BY resource_type;
```

## Security Notes

- All API keys should be kept secure and not committed to version control
- Service role key has elevated privileges - use carefully
- RLS policies protect user data but require proper authentication
- Consider rate limiting at the application level for additional protection 