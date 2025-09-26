from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from authlib.integrations.httpx_client import AsyncOAuth2Client
from motor.motor_asyncio import AsyncIOMotorDatabase
from services.auth_service import AuthService
from database import get_database
from config import settings
import secrets

router = APIRouter()

# OAuth configurations
GOOGLE_CLIENT_ID = settings.google_client_id
GOOGLE_CLIENT_SECRET = settings.google_client_secret
APPLE_CLIENT_ID = settings.apple_client_id
APPLE_CLIENT_SECRET = settings.apple_client_secret

# OAuth URLs
GOOGLE_AUTHORIZATION_URL = "https://accounts.google.com/o/oauth2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

APPLE_AUTHORIZATION_URL = "https://appleid.apple.com/auth/authorize"
APPLE_TOKEN_URL = "https://appleid.apple.com/auth/token"
APPLE_USERINFO_URL = "https://appleid.apple.com/auth/keys"

@router.get("/google/login")
async def google_login(request: Request):
    """Initiate Google OAuth login"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    google = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri="http://localhost:8000/auth/oauth/google/callback"
    )

    authorization_url, _ = google.create_authorization_url(
        GOOGLE_AUTHORIZATION_URL,
        state=state,
        scope=["openid", "email", "profile"]
    )

    return RedirectResponse(authorization_url)

@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str):
    """Handle Google OAuth callback"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth not configured"
        )

    # Verify state for CSRF protection
    if state != request.session.get("oauth_state"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    google = AsyncOAuth2Client(
        client_id=GOOGLE_CLIENT_ID,
        client_secret=GOOGLE_CLIENT_SECRET,
        redirect_uri="http://localhost:8000/auth/oauth/google/callback"
    )

    try:
        token = await google.fetch_token(
            GOOGLE_TOKEN_URL,
            authorization_response=str(request.url),
            code=code
        )

        # Get user info
        user_info = await google.get(GOOGLE_USERINFO_URL)
        user_data = user_info.json()

        # Create or get user
        db = await get_database()
        auth_service = AuthService(db)

        user = await auth_service.create_oauth_user(
            email=user_data["email"],
            username=user_data.get("name", user_data["email"].split("@")[0]),
            provider="google",
            provider_id=user_data["id"]
        )

        # Create access token
        access_token = auth_service.create_access_token(data={"sub": user.email})

        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/auth/callback?token={access_token}&provider=google"
        return RedirectResponse(frontend_url)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )

@router.get("/apple/login")
async def apple_login(request: Request):
    """Initiate Apple OAuth login"""
    if not APPLE_CLIENT_ID or not APPLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple OAuth not configured"
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)
    request.session["oauth_state"] = state

    apple = AsyncOAuth2Client(
        client_id=APPLE_CLIENT_ID,
        client_secret=APPLE_CLIENT_SECRET,
        redirect_uri="http://localhost:8000/auth/oauth/apple/callback"
    )

    authorization_url, _ = apple.create_authorization_url(
        APPLE_AUTHORIZATION_URL,
        state=state,
        scope=["name", "email"]
    )

    return RedirectResponse(authorization_url)

@router.get("/apple/callback")
async def apple_callback(request: Request, code: str, state: str):
    """Handle Apple OAuth callback"""
    if not APPLE_CLIENT_ID or not APPLE_CLIENT_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Apple OAuth not configured"
        )

    # Verify state for CSRF protection
    if state != request.session.get("oauth_state"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid state parameter"
        )

    apple = AsyncOAuth2Client(
        client_id=APPLE_CLIENT_ID,
        client_secret=APPLE_CLIENT_SECRET,
        redirect_uri="http://localhost:8000/auth/oauth/apple/callback"
    )

    try:
        token = await apple.fetch_token(
            APPLE_TOKEN_URL,
            authorization_response=str(request.url),
            code=code
        )

        # For Apple, we need to decode the ID token to get user info
        # This is a simplified version - in production, you'd validate the token properly
        id_token = token.get("id_token")
        if not id_token:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No ID token received from Apple"
            )

        # For now, we'll assume the email is provided in the form data
        # In a real implementation, you'd decode and validate the JWT
        user_email = request.query_params.get("user_email")
        user_name = request.query_params.get("user_name", "Apple User")

        if not user_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Apple"
            )

        # Create or get user
        db = await get_database()
        auth_service = AuthService(db)

        user = await auth_service.create_oauth_user(
            email=user_email,
            username=user_name,
            provider="apple",
            provider_id=token.get("sub", user_email)  # Use sub claim or email as fallback
        )

        # Create access token
        access_token = auth_service.create_access_token(data={"sub": user.email})

        # Redirect to frontend with token
        frontend_url = f"http://localhost:3000/auth/callback?token={access_token}&provider=apple"
        return RedirectResponse(frontend_url)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"OAuth authentication failed: {str(e)}"
        )
