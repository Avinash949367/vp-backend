from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
from motor.motor_asyncio import AsyncIOMotorDatabase
from models import User, UserCreate, TokenData
from config import settings
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import secrets
import string

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
        return encoded_jwt

    async def authenticate_user(self, email: str, password: str) -> Optional[User]:
        user = await self.db.users.find_one({"email": email})
        if not user:
            return None
        if not self.verify_password(password, user["hashed_password"]):
            return None
        return User(**user)

    async def get_user_by_email(self, email: str) -> Optional[User]:
        user = await self.db.users.find_one({"email": email})
        return User(**user) if user else None

    async def create_user(self, user: UserCreate) -> User:
        # Check if user already exists
        existing_user = await self.db.users.find_one({"email": user.email})
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        user_dict = {
            "email": user.email,
            "username": user.username,
            "name": user.name,
            "hashed_password": self.get_password_hash(user.password),
            "created_at": datetime.utcnow(),
            "profile": {}
        }

        result = await self.db.users.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        return User(**user_dict)

    async def create_oauth_user(self, email: str, username: str, provider: str, provider_id: str) -> User:
        # Check if user already exists
        existing_user = await self.db.users.find_one({"email": email})
        if existing_user:
            return User(**existing_user)

        user_dict = {
            "email": email,
            "username": username,
            "hashed_password": "",  # OAuth users don't have passwords
            "created_at": datetime.utcnow(),
            "profile": {
                "oauth_provider": provider,
                "oauth_id": provider_id
            }
        }

        result = await self.db.users.insert_one(user_dict)
        user_dict["_id"] = result.inserted_id
        return User(**user_dict)

    def generate_password_reset_token(self) -> str:
        """Generate a secure password reset token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for i in range(32))

    async def create_password_reset_request(self, email: str) -> str:
        """Create a password reset request and return the token"""
        user = await self.get_user_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )

        reset_token = self.generate_password_reset_token()
        expiry = datetime.utcnow() + timedelta(hours=24)  # Token expires in 24 hours

        # Store reset token in database
        await self.db.password_resets.insert_one({
            "email": email,
            "token": reset_token,
            "created_at": datetime.utcnow(),
            "expires_at": expiry
        })

        return reset_token

    async def reset_password(self, token: str, new_password: str) -> bool:
        """Reset password using token"""
        reset_request = await self.db.password_resets.find_one({
            "token": token,
            "expires_at": {"$gt": datetime.utcnow()}
        })

        if not reset_request:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired reset token"
            )

        # Update user password
        hashed_password = self.get_password_hash(new_password)
        await self.db.users.update_one(
            {"email": reset_request["email"]},
            {"$set": {"hashed_password": hashed_password}}
        )

        # Delete used reset token
        await self.db.password_resets.delete_one({"token": token})

        return True

    async def send_password_reset_email(self, email: str, reset_token: str):
        """Send password reset email"""
        if not all([settings.smtp_server, settings.smtp_username, settings.smtp_password]):
            # If SMTP not configured, just return the token for development
            print(f"Password reset token for {email}: {reset_token}")
            return

        msg = MIMEMultipart()
        msg['From'] = settings.from_email
        msg['To'] = email
        msg['Subject'] = "Password Reset - TravelMate"

        reset_link = f"http://localhost:3000/reset-password?token={reset_token}"

        body = f"""
        Hi there,

        You requested a password reset for your TravelMate account.

        Click the link below to reset your password:
        {reset_link}

        This link will expire in 24 hours.

        If you didn't request this reset, please ignore this email.

        Best regards,
        TravelMate Team
        """

        msg.attach(MIMEText(body, 'plain'))

        try:
            server = smtplib.SMTP(settings.smtp_server, settings.smtp_port)
            server.starttls()
            server.login(settings.smtp_username, settings.smtp_password)
            text = msg.as_string()
            server.sendmail(settings.from_email, email, text)
            server.quit()
        except Exception as e:
            print(f"Failed to send email: {e}")

    async def verify_token(self, token: str) -> Optional[TokenData]:
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
            email: str = payload.get("sub")
            if email is None:
                return None
            return TokenData(email=email)
        except JWTError:
            return None

    async def update_user_profile(self, user_id: str, update_data: Dict[str, Any]) -> User:
        """Update user profile information"""
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No data to update")
        
        # Update the user document
        result = await self.db.users.update_one(
            {"_id": user_id},
            {"$set": update_data}
        )
        
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Return updated user
        updated_user = await self.db.users.find_one({"_id": user_id})
        return User(**updated_user)

    async def update_user_password(self, user_id: str, new_password: str) -> bool:
        """Update user password"""
        hashed_password = self.get_password_hash(new_password)
        
        result = await self.db.users.update_one(
            {"_id": user_id},
            {"$set": {"hashed_password": hashed_password}}
        )
        
        return result.modified_count > 0