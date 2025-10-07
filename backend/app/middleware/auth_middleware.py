import logging
from typing import Optional, Callable, Dict, Any
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import sys
from pathlib import Path

# Add app directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import services
from app.services.auth_service import AuthService

logger = logging.getLogger("bpt-auth-middleware")

# Initialize security scheme
security = HTTPBearer()

# Create auth service
auth_service = AuthService()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> Dict[str, Any]:
    """
    Dependency that validates the access token and returns the current user
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Dict containing user information
        
    Raises:
        HTTPException: If token is invalid or expired
    """
    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )
        
    # For testing mode with mock users
    if os.getenv("USE_MOCK_USERS", "false").lower() == "true":
        return {
            "id": "mock-user-id",
            "email": "mock@example.com",
            "role": "user",
            "is_mock": True
        }
    
    # Verify token
    token = credentials.credentials
    result = await auth_service.verify_token(token)
    
    if not result.get("success"):
        raise HTTPException(
            status_code=401,
            detail=f"Invalid authentication token: {result.get('error', 'Unknown error')}",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    # Return user data
    return result.get("user")

async def get_admin_user(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """
    Dependency that ensures the user is an admin
    
    Args:
        user: User data from get_current_user dependency
        
    Returns:
        Dict containing user information if user is an admin
        
    Raises:
        HTTPException: If user is not an admin
    """
    # For testing mode with mock admin
    if user.get("is_mock") and os.getenv("USE_MOCK_USERS", "false").lower() == "true":
        return {
            "id": "mock-admin-id",
            "email": "admin@example.com",
            "role": "admin",
            "is_mock": True
        }
    
    # Check if user is an admin
    user_role = user.get("user_metadata", {}).get("role")
    if user_role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions. Admin role required."
        )
    
    return user

class RoleChecker:
    """
    Dependency class for checking user roles
    
    Usage:
        require_roles = RoleChecker(['admin', 'editor'])
        @app.get('/admin-only', dependencies=[Depends(require_roles)])
    """
    
    def __init__(self, allowed_roles: list):
        self.allowed_roles = allowed_roles
        
    async def __call__(self, user: Dict[str, Any] = Depends(get_current_user)):
        # For testing mode with mock users
        if user.get("is_mock") and os.getenv("USE_MOCK_USERS", "false").lower() == "true":
            # Check if requested role is in allowed_roles
            requested_role = os.getenv("MOCK_USER_ROLE", "user")
            if requested_role in self.allowed_roles:
                return user
            else:
                raise HTTPException(
                    status_code=403,
                    detail=f"User with role '{requested_role}' not allowed"
                )
        
        # Check user role
        user_role = user.get("user_metadata", {}).get("role", "user")
        
        if user_role not in self.allowed_roles:
            raise HTTPException(
                status_code=403,
                detail=f"User with role '{user_role}' not allowed. Required roles: {self.allowed_roles}"
            )
            
        return user 