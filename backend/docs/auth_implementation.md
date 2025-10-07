# Authentication and User Management Implementation

This document outlines the authentication and user management implementation for the BPT (Big Picture Trading) application.

## Overview

The authentication system leverages Supabase Auth to handle user registration, login, session management, and other authentication-related features. The system is designed to be secure, scalable, and easy to integrate with other parts of the application.

## Components

1. **Auth Service (`app/services/auth_service.py`)**:
   - Core service that interacts with Supabase Auth
   - Handles user registration, login, logout
   - Manages tokens and session verification
   - Supports password reset functionality
   - Includes fallback to mock mode for testing

2. **Authentication Middleware (`app/middleware/auth_middleware.py`)**:
   - Provides FastAPI dependencies for securing endpoints
   - Includes `get_current_user` for basic authentication
   - Provides `get_admin_user` for admin-only endpoints
   - Includes `RoleChecker` for role-based access control

3. **User Models (`app/models/user.py`)**:
   - Defines Pydantic models for user data
   - Includes models for user registration, login, responses
   - Defines token response formats
   - Includes role definitions for authorization

4. **Authentication Routes (`app/routes/auth_routes.py`)**:
   - Implements API endpoints for authentication
   - Includes registration, login, logout endpoints
   - Provides user profile management
   - Supports token refresh and password reset

5. **Supabase Database Setup (`scripts/setup_user_management.sql`)**:
   - Creates necessary tables for user management
   - Sets up row-level security (RLS) policies
   - Implements database triggers for user registration
   - Establishes relationships between users, companies, and transcripts

## Database Schema

The user management system includes the following tables:

1. **user_profiles**:
   - Extends Supabase Auth users with additional profile information
   - Stores first name, last name, company, role

2. **companies**:
   - Stores company information
   - Includes name, domain, creation date

3. **company_users**:
   - Maps users to companies (many-to-many relationship)
   - Includes role within company (member, admin)

4. **transcript_access**:
   - Controls which users/companies have access to which transcripts
   - Includes access level (read, write, owner)

## Security Implementation

1. **Token-based Authentication**:
   - JWT tokens issued by Supabase Auth
   - Access tokens with configurable expiration
   - Refresh tokens for extended sessions

2. **Row-Level Security (RLS)**:
   - Database-level security policies
   - Ensures users can only access their own data
   - Controls access to shared resources based on permissions

3. **Role-based Access Control**:
   - Supports different user roles: admin, user, editor, viewer
   - API endpoints protected based on role requirements
   - Role enforcement at both API and database levels

## Deployment and Setup

### Setting Up User Management

The user management tables and policies can be set up using the provided script:

```bash
# Check if user management is already set up
python scripts/setup_user_management.py check

# Set up user management tables and policies
python scripts/setup_user_management.py setup
```

Alternatively, you can use the API endpoint:

```
GET /setup/user-management?admin_secret=YOUR_ADMIN_SECRET
```

### Environment Variables

The authentication system requires the following environment variables:

- `SUPABASE_URL`: URL of your Supabase project
- `SUPABASE_KEY`: Anon/Public key for your Supabase project
- `ADMIN_SECRET`: Secret for admin operations (optional, defaults to "change-me-in-production")
- `USE_MOCK_USERS`: Set to "true" to use mock users for testing

## Testing

The authentication system can be tested using the provided test script:

```bash
# Test the full authentication implementation (requires Supabase connection)
python scripts/test_auth_implementation.py

# Test in mock mode (no real Supabase connection needed)
python scripts/test_auth_implementation.py --mock

# Test API endpoints only
python scripts/test_auth_implementation.py --api
```

This script tests:
1. User registration and login
2. User management (getting users, updating roles, listing users)
3. Transcript sharing functionality
4. API endpoints for authentication and transcript access

### Test Users

The test script creates two test users:
- Regular user: test_user@example.com
- Admin user: test_admin@example.com

If these users already exist, the script will attempt to log in with them instead of creating new ones.

### Mock Mode

When testing without a real Supabase connection, you can use the mock mode by setting the `USE_MOCK_SUPABASE` environment variable to "true" or using the `--mock` flag in the test script. In mock mode, all Supabase operations will return predefined responses.

Similarly, when testing API endpoints, you can use the `USE_MOCK_USERS` environment variable to bypass actual authentication checks.

## Integration with Frontend

Frontend applications should:

1. Use the `/api/auth/register` endpoint for user registration
2. Use the `/api/auth/login` endpoint to obtain access and refresh tokens
3. Include the access token in the `Authorization` header for all authenticated requests
4. Use the `/api/auth/refresh` endpoint to refresh the access token when needed
5. Use the `/api/auth/logout` endpoint to end user sessions

### Transcript Access Control

After a user logs in, they can:

1. View transcripts they have access to via `/api/transcripts/`
2. Get details of a specific transcript via `/api/transcripts/{transcript_id}`
3. Share a transcript with another user via `/api/transcripts/{transcript_id}/share`
4. Remove transcript sharing via `/api/transcripts/{transcript_id}/share` (DELETE)
5. View who has access to a transcript via `/api/transcripts/{transcript_id}/access`

## Implementation Status

The authentication and user management system is fully implemented with the following features:

- ✅ User registration and login with email/password
- ✅ JWT token-based authentication
- ✅ Password reset functionality
- ✅ User profile management
- ✅ Role-based access control
- ✅ Transcript access management (sharing and unsharing)
- ✅ Admin operations (listing users, updating roles)
- ✅ Row-Level Security policies in the database

## Future Enhancements

Planned enhancements for the authentication system include:

1. OAuth integration for social login (Google, GitHub, etc.)
2. Multi-factor authentication support
3. Enhanced audit logging for security events
4. IP-based security restrictions
5. Automated account lockout after failed login attempts
6. Team/Organization management
7. Subscription and billing integration

## Troubleshooting

Common issues and their solutions:

1. **401 Unauthorized errors**: Check that your token is valid and not expired
2. **403 Forbidden errors**: Verify that the user has the correct role for the requested resource
3. **Database permission errors**: Ensure RLS policies are correctly set up
4. **Token refresh failures**: Verify that the refresh token is valid and not expired

### Debugging Environment Variables

For debugging, you can set the following environment variables:
- `USE_MOCK_SUPABASE=true` - Use mock responses instead of real Supabase connections
- `USE_MOCK_USERS=true` - Bypass authentication checks in API endpoints
- `LOG_LEVEL=DEBUG` - Enable more detailed logging 