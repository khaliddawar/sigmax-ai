-- Create a function to execute arbitrary SQL (for admin use only)
-- WARNING: This is potentially dangerous if exposed to untrusted users
-- This function should only be used in development/testing environments
-- For production, implement specific functions for each operation

CREATE OR REPLACE FUNCTION exec_sql(sql text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER -- Runs with the privileges of the function creator
AS $$
DECLARE
  result json;
BEGIN
  EXECUTE sql;
  result := json_build_object('success', true, 'message', 'SQL executed successfully');
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  result := json_build_object('success', false, 'message', SQLERRM, 'error', SQLSTATE);
  RETURN result;
END;
$$;

-- For security, restrict who can execute this function
REVOKE EXECUTE ON FUNCTION exec_sql(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION exec_sql(text) TO authenticated;
GRANT EXECUTE ON FUNCTION exec_sql(text) TO anon;

-- Create a safer function to check if an extension exists
CREATE OR REPLACE FUNCTION check_extension_exists(extension_name text)
RETURNS json
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
  result json;
  extension_exists boolean;
BEGIN
  SELECT EXISTS (
    SELECT 1 FROM pg_extension WHERE extname = extension_name
  ) INTO extension_exists;
  
  result := json_build_object(
    'success', true, 
    'extension_name', extension_name,
    'exists', extension_exists
  );
  RETURN result;
EXCEPTION WHEN OTHERS THEN
  result := json_build_object('success', false, 'message', SQLERRM, 'error', SQLSTATE);
  RETURN result;
END;
$$;

-- Grant execute permissions
REVOKE EXECUTE ON FUNCTION check_extension_exists(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION check_extension_exists(text) TO authenticated;
GRANT EXECUTE ON FUNCTION check_extension_exists(text) TO anon; 