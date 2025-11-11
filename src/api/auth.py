"""
Google OAuth authentication for user sign-in
Simple session-based authentication for MVP
"""

from fastapi import APIRouter, Request, HTTPException, Response
from fastapi.responses import RedirectResponse, HTMLResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from itsdangerous import URLSafeTimedSerializer
import os
import logging
from typing import Optional

from src.models.user_store import user_store

logger = logging.getLogger(__name__)

# Load environment variables
config = Config('.env')

# OAuth setup
oauth = OAuth(config)
oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={
        'scope': 'openid email profile'
    }
)

# Session management
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-in-production')
serializer = URLSafeTimedSerializer(SECRET_KEY)

# Router
router = APIRouter(prefix="/auth", tags=["authentication"])


def create_session_token(user_id: str) -> str:
    """Create a secure session token"""
    return serializer.dumps(user_id)


def verify_session_token(token: str) -> Optional[str]:
    """Verify and decode session token"""
    try:
        user_id = serializer.loads(token, max_age=86400 * 7)  # 7 days
        return user_id
    except Exception as e:
        logger.error(f"Invalid session token: {e}")
        return None


async def get_current_user(request: Request) -> Optional[dict]:
    """Get current user from session"""
    # Use Starlette's built-in session
    user_id = request.session.get('user_id')
    print(f"get_current_user - user_id from session: {user_id}")
    
    if not user_id:
        print("No user_id in session")
        return None
    
    user = user_store.get_user(user_id)
    print(f"User retrieved from store: {bool(user)}")
    return user


@router.get("/login")
async def login(request: Request):
    """Redirect to Google OAuth"""
    redirect_uri = request.url_for('auth_callback')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@router.get("/callback")
async def auth_callback(request: Request):
    """Handle Google OAuth callback"""
    try:
        print("=== OAuth callback triggered ===")
        
        # Get token from Google
        token = await oauth.google.authorize_access_token(request)
        print(f"Token received: {bool(token)}")
        
        # Get user info
        user_info = token.get('userinfo')
        if not user_info:
            print("ERROR: No userinfo in token")
            raise HTTPException(status_code=400, detail="Failed to get user info")
        
        google_id = user_info.get('sub')
        email = user_info.get('email')
        name = user_info.get('name')
        
        print(f"User authenticated: {email}")
        
        # Check if user exists
        user = user_store.get_user_by_google_id(google_id)
        
        if not user:
            # Create new user
            print(f"Creating new user: {email}")
            user_data = {
                'google_id': google_id,
                'email': email,
                'name': name,
                'phone': ''  # User will add later
            }
            user_id = user_store.create_user(user_data)
            user = user_store.get_user(user_id)
            print(f"User created with ID: {user_id}")
        else:
            user_id = user['user_id']
            print(f"Existing user logged in: {user_id}")
        
        # Create session using Starlette's session
        request.session['user_id'] = user_id
        print(f"Session set in request.session: {user_id}")
        
        # Redirect to dashboard
        response = RedirectResponse(url='/dashboard', status_code=302)
        print("Redirecting to dashboard")
        return response
        
    except Exception as e:
        print(f"OAuth callback error: {e}")
        logger.error(f"OAuth callback error: {e}", exc_info=True)
        raise HTTPException(status_code=400, detail=f"Authentication failed: {str(e)}")


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    request.session.clear()
    response = RedirectResponse(url='/')
    return response


@router.get("/me")
async def get_me(request: Request):
    """Get current user info"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


@router.post("/update-profile")
async def update_profile(request: Request):
    """Update user profile"""
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        body = await request.json()
        user_id = user['user_id']
        
        # Update user
        updates = {}
        if 'phone' in body:
            updates['phone'] = body['phone']
        if 'name' in body:
            updates['name'] = body['name']
        
        success = user_store.update_user(user_id, updates)
        
        if success:
            return {"message": "Profile updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update profile")
            
    except Exception as e:
        logger.error(f"Error updating profile: {e}")
        raise HTTPException(status_code=400, detail=str(e))
