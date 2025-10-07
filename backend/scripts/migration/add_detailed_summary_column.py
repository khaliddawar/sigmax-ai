#!/usr/bin/env python3
"""
Migration script to add detailed_summary column to transcripts table

This fixes the warning: "detailed_summary column needs migration"
"""

import os
import sys
import logging
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_detailed_summary_column():
    """Add detailed_summary column to transcripts table"""
    
    try:
        # Load environment variables
        from dotenv import load_dotenv
        load_dotenv()
        
        # Import Supabase service
        from app.services.supabase_client import SupabaseService
        
        logger.info("🚀 Starting detailed_summary column migration...")
        
        # Initialize Supabase service
        supabase_service = SupabaseService()
        
        # Check connection
        connection_result = supabase_service.check_connection()
        if not connection_result.get('success'):
            logger.error(f"❌ Supabase connection failed: {connection_result.get('error')}")
            return False
        
        logger.info("✅ Supabase connection successful")
        
        # SQL to add the detailed_summary column
        migration_sql = """
        -- Add detailed_summary column to transcripts table
        ALTER TABLE transcripts 
        ADD COLUMN IF NOT EXISTS detailed_summary TEXT;
        
        -- Add comment to document the column purpose
        COMMENT ON COLUMN transcripts.detailed_summary IS 'Full summary content without size restrictions';
        """
        
        logger.info("📝 Executing migration SQL...")
        
        # Execute the migration using raw SQL
        try:
            # Use the Supabase client to execute raw SQL
            result = supabase_service.client.rpc('exec_sql', {'sql': migration_sql}).execute()
            
            if hasattr(result, 'error') and result.error is not None:
                logger.error(f"❌ Migration failed: {result.error}")
                return False
                
            logger.info("✅ Migration SQL executed successfully")
            
        except Exception as e:
            # If RPC doesn't work, try alternative approach
            logger.warning(f"RPC approach failed: {e}")
            logger.info("Trying alternative approach...")
            
            # Alternative: Use PostgREST to add column
            # This might not work directly, but we can try
            try:
                # Check if column already exists by trying to select it
                test_result = supabase_service.client.table("transcripts").select("detailed_summary").limit(1).execute()
                
                if hasattr(test_result, 'error') and test_result.error is not None:
                    if "column" in str(test_result.error).lower() and "does not exist" in str(test_result.error).lower():
                        logger.error("❌ Column doesn't exist and cannot be added via PostgREST")
                        logger.error("Please run this SQL manually in your Supabase SQL editor:")
                        logger.error(migration_sql)
                        return False
                    else:
                        logger.error(f"❌ Unexpected error: {test_result.error}")
                        return False
                else:
                    logger.info("✅ Column already exists!")
                    
            except Exception as e2:
                logger.error(f"❌ Alternative approach also failed: {e2}")
                logger.error("Please run this SQL manually in your Supabase SQL editor:")
                logger.error(migration_sql)
                return False
        
        # Verify the migration
        logger.info("🔍 Verifying migration...")
        
        try:
            # Try to select the new column
            verify_result = supabase_service.client.table("transcripts").select("detailed_summary").limit(1).execute()
            
            if hasattr(verify_result, 'error') and verify_result.error is not None:
                logger.error(f"❌ Verification failed: {verify_result.error}")
                return False
            
            logger.info("✅ Migration verified successfully!")
            logger.info("✅ detailed_summary column is now available")
            
            # Update the Supabase service to use the new column
            logger.info("🔄 The application will now store full summaries in detailed_summary column")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Verification failed: {e}")
            return False
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = add_detailed_summary_column()
    
    if success:
        logger.info("\n🎉 MIGRATION COMPLETED SUCCESSFULLY!")
        logger.info("The 'detailed_summary column needs migration' warning should now be resolved.")
        logger.info("Future summaries will be stored in the detailed_summary column without truncation.")
    else:
        logger.error("\n❌ MIGRATION FAILED!")
        logger.error("Please run the SQL manually in your Supabase dashboard.")
        
    sys.exit(0 if success else 1) 