from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
import uuid

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import services and middlewares
from app.services.supabase_client import SupabaseService
from app.services.retrieval_qa_service import RetrievalQAService
from app.middleware.auth_middleware import get_current_user, RoleChecker

# Initialize logger
logger = logging.getLogger("bpt-transcript-routes")

# Initialize router
router = APIRouter(prefix="/transcripts", tags=["transcripts"])

# Initialize services
supabase_service = SupabaseService()

# Create role checkers
require_admin = RoleChecker(["admin"])
require_editor = RoleChecker(["admin", "editor"])

@router.get("/", dependencies=[Depends(get_current_user)])
async def get_all_transcripts(
    user: Dict[str, Any] = Depends(get_current_user),
    limit: int = 100,
    offset: int = 0
):
    """
    Get all transcripts the user has access to
    """
    logger.info(f"Getting transcripts for user: {user.get('id')}")
    
    # Get transcripts from Supabase
    result = await supabase_service.get_transcripts()
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error retrieving transcripts")
        logger.error(f"Error retrieving transcripts: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving transcripts: {error_msg}"
        )
    
    # Extract transcripts
    transcripts = result.get("data", [])
    
    # Return paginated results
    return {
        "success": True,
        "count": len(transcripts),
        "transcripts": transcripts[offset:offset+limit]
    }

@router.get("/{transcript_id}", dependencies=[Depends(get_current_user)])
async def get_transcript_by_id(
    transcript_id: str,
    user: Dict[str, Any] = Depends(get_current_user),
    include_chunks: bool = False
):
    """
    Get a transcript by ID if the user has access to it
    """
    logger.info(f"Getting transcript {transcript_id} for user: {user.get('id')}")
    
    # Get transcript from Supabase
    result = await supabase_service.get_transcript_by_id(transcript_id)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error retrieving transcript")
        logger.error(f"Error retrieving transcript {transcript_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transcript not found or access denied: {error_msg}"
        )
    
    # Return transcript with or without chunks
    if include_chunks:
        return result
    else:
        # Remove chunks to reduce response size
        result_without_chunks = result.copy()
        if "chunks" in result_without_chunks:
            del result_without_chunks["chunks"]
        return result_without_chunks

@router.get("/{transcript_id}/key-points", dependencies=[Depends(get_current_user)])
async def get_transcript_key_points(
    transcript_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get key points for a transcript if the user has access to it
    """
    logger.info(f"Getting key points for transcript {transcript_id} for user: {user.get('id')}")
    
    # Get key points from Supabase
    result = await supabase_service.get_key_points(transcript_id)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error retrieving key points")
        logger.error(f"Error retrieving key points for transcript {transcript_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Key points not found or access denied: {error_msg}"
        )
    
    return result

@router.post("/{transcript_id}/share", dependencies=[Depends(get_current_user)])
async def share_transcript(
    transcript_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Share a transcript with another user or company
    """
    # Get request data
    data = await request.json()
    shared_with_user_id = data.get("user_id")
    shared_with_company_id = data.get("company_id")
    access_level = data.get("access_level", "read")
    
    if not shared_with_user_id and not shared_with_company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or company_id must be provided"
        )
    
    logger.info(f"Sharing transcript {transcript_id} from user {user.get('id')} with user {shared_with_user_id} or company {shared_with_company_id}")
    
    # Share transcript using SupabaseService
    result = await supabase_service.share_transcript(
        transcript_id=transcript_id,
        user_id=shared_with_user_id,
        company_id=shared_with_company_id,
        access_level=access_level
    )
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error sharing transcript")
        logger.error(f"Error sharing transcript {transcript_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error sharing transcript: {error_msg}"
        )
    
    return {
        "success": True,
        "transcript_id": transcript_id,
        "shared_with": shared_with_user_id or shared_with_company_id,
        "access_level": access_level
    }

@router.delete("/{transcript_id}/share", dependencies=[Depends(get_current_user)])
async def remove_transcript_share(
    transcript_id: str,
    request: Request,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Remove a transcript share from a user or company
    """
    # Get request data
    data = await request.json()
    shared_with_user_id = data.get("user_id")
    shared_with_company_id = data.get("company_id")
    
    if not shared_with_user_id and not shared_with_company_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either user_id or company_id must be provided"
        )
    
    logger.info(f"Removing share for transcript {transcript_id} from user {shared_with_user_id} or company {shared_with_company_id}")
    
    # Remove transcript share using SupabaseService
    result = await supabase_service.remove_transcript_share(
        transcript_id=transcript_id,
        user_id=shared_with_user_id,
        company_id=shared_with_company_id
    )
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error removing transcript share")
        logger.error(f"Error removing transcript share {transcript_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error removing transcript share: {error_msg}"
        )
    
    return {
        "success": True,
        "transcript_id": transcript_id,
        "message": "Share removed successfully"
    }

@router.get("/{transcript_id}/access", dependencies=[Depends(get_current_user)])
async def get_transcript_access(
    transcript_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get all users and companies that have access to a transcript
    """
    logger.info(f"Getting access information for transcript {transcript_id}")
    
    # Get transcript access using SupabaseService
    result = await supabase_service.get_transcript_access(transcript_id)
    
    if not result.get("success"):
        error_msg = result.get("error", "Unknown error getting transcript access")
        logger.error(f"Error getting access for transcript {transcript_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error getting transcript access: {error_msg}"
        )
    
    return result

@router.delete("/{transcript_id}", dependencies=[Depends(get_current_user)])
async def delete_transcript(
    transcript_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Delete a transcript and all its related data.
    
    This endpoint safely removes:
    - The transcript record
    - All transcript chunks
    - All semantic chunks
    - Key points analysis
    - Transcript sharing permissions
    
    This action cannot be undone.
    """
    if not transcript_id:
        raise HTTPException(status_code=400, detail="Transcript ID is required")
        
    if not supabase_service.is_connected():
        raise HTTPException(status_code=500, detail="Database not connected")
    
    logger.info(f"DELETE request received for transcript {transcript_id} from user {user.get('id')}")
        
    response = await supabase_service.delete_transcript(transcript_id)
    
    if not response["success"]:
        error_message = response.get("error", "Failed to delete transcript")
        logger.error(f"Failed to delete transcript {transcript_id}: {error_message}")
        
        # Return appropriate HTTP status codes
        if "not found" in error_message.lower():
            raise HTTPException(status_code=404, detail=error_message)
        else:
            raise HTTPException(status_code=500, detail=error_message)
    
    # Log successful deletion
    logger.info(f"✅ Successfully deleted transcript {transcript_id}")
    logger.info(f"   Total items deleted: {response.get('total_deleted', 0)}")
    logger.info(f"   Processing time: {response.get('processing_time', 0):.2f}s")
        
    return response 