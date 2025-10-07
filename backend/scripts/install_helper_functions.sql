-- Install helper functions for pgvector integration
-- Run this script in your Supabase SQL editor

-- Function to check if an extension exists
CREATE OR REPLACE FUNCTION check_extension_exists(extension_name text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER -- Runs with the privileges of the function creator
AS $$
DECLARE
  result jsonb;
  exists_val boolean;
BEGIN
  SELECT EXISTS(
    SELECT 1 FROM pg_extension WHERE extname = extension_name
  ) INTO exists_val;
  
  result := jsonb_build_object(
    'success', true,
    'exists', exists_val,
    'extension_name', extension_name
  );
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  result := jsonb_build_object(
    'success', false,
    'message', SQLERRM,
    'error', SQLSTATE,
    'extension_name', extension_name
  );
  RETURN result;
END;
$$;

-- Grant permission to anonymous users to execute this function
GRANT EXECUTE ON FUNCTION check_extension_exists(text) TO anon;
GRANT EXECUTE ON FUNCTION check_extension_exists(text) TO authenticated;
GRANT EXECUTE ON FUNCTION check_extension_exists(text) TO service_role;

-- Function to execute arbitrary SQL (for admin use only)
-- WARNING: This is potentially dangerous if exposed to untrusted users
-- Use with caution and only grant permissions to trusted roles
CREATE OR REPLACE FUNCTION exec_sql(sql text)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER -- Runs with the privileges of the function creator
AS $$
DECLARE
  result jsonb;
BEGIN
  EXECUTE sql;
  result := jsonb_build_object('success', true, 'message', 'SQL executed successfully');
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  result := jsonb_build_object('success', false, 'message', SQLERRM, 'error', SQLSTATE);
  RETURN result;
END;
$$;

-- IMPORTANT: Restrict who can execute this function
-- Only grant to service_role (server-side) for safety
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM anon;
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM authenticated;
GRANT EXECUTE ON FUNCTION exec_sql(text) TO service_role;

-- This function should only be called from server-side code with admin privileges
COMMENT ON FUNCTION exec_sql IS 'Execute arbitrary SQL. WARNING: Security risk if exposed to untrusted users. Use only with service_role.'; 