from fastapi import APIRouter, Depends, HTTPException, status, Request
from datetime import timedelta, datetime
from models import UserCreate, UserLogin, Token, User, UserUpdate, PasswordChangeRequest
from services.auth_service import AuthService
from database import get_database
from config import settings
from auth import get_current_user
from pydantic import BaseModel

router = APIRouter()

@router.post("/register", response_model=Token)
async def register(user: UserCreate):
    db = await get_database()
    auth_service = AuthService(db)

    try:
        new_user = await auth_service.create_user(user)
        access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
        access_token = auth_service.create_access_token(
            data={"sub": new_user.email}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin):
    db = await get_database()
    auth_service = AuthService(db)
    user = await auth_service.authenticate_user(user_credentials.email, user_credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth_service.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/password-reset/request")
async def password_reset_request(email: str):
    db = await get_database()
    auth_service = AuthService(db)
    reset_token = await auth_service.create_password_reset_request(email)
    await auth_service.send_password_reset_email(email, reset_token)
    return {"message": "Password reset email sent if the email is registered."}

@router.post("/password-reset/confirm")
async def password_reset_confirm(token: str, new_password: str):
    db = await get_database()
    auth_service = AuthService(db)
    success = await auth_service.reset_password(token, new_password)
    if success:
        return {"message": "Password has been reset successfully."}
    else:
        raise HTTPException(status_code=400, detail="Password reset failed.")

class UserUpdateRequest(BaseModel):
    name: str = None
    profile_picture: str = None


@router.put("/profile")
async def update_profile(user_update: UserUpdateRequest, current_user: User = Depends(get_current_user)):
    db = await get_database()
    auth_service = AuthService(db)
    
    try:
        updated_user = await auth_service.update_user_profile(current_user.id, user_update.dict(exclude_unset=True))
        return updated_user
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to update profile: {str(e)}")

@router.put("/change-password")
async def change_password(password_data: PasswordChangeRequest, current_user: User = Depends(get_current_user)):
    db = await get_database()
    auth_service = AuthService(db)
    
    try:
        # Verify current password
        user = await auth_service.authenticate_user(current_user.email, password_data.current_password)
        if not user:
            raise HTTPException(status_code=400, detail="Current password is incorrect")
        
        # Update password
        success = await auth_service.update_user_password(current_user.id, password_data.new_password)
        if success:
            return {"message": "Password updated successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to update password")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to change password: {str(e)}")
