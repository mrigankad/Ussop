"""
Authentication Service for Ussop
JWT-based authentication with RBAC
"""
import uuid
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from functools import wraps

from fastapi import HTTPException, Depends, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from config.settings import settings
from models.database import get_db
from models.auth import User, UserSession, Role, init_default_roles, create_default_admin
from services.monitoring import get_audit_logger


# JWT Configuration
SECRET_KEY = settings.SECRET_KEY
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.ACCESS_TOKEN_EXPIRE_MINUTES
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Security scheme for FastAPI
security = HTTPBearer(auto_error=False)


class AuthService:
    """Authentication and authorization service."""
    
    def __init__(self):
        self.audit = get_audit_logger()
    
    def create_access_token(
        self,
        user_id: str,
        session_id: str,
        expires_delta: Optional[timedelta] = None
    ) -> Tuple[str, str]:
        """
        Create JWT access token.
        
        Returns:
            (token, jti)
        """
        jti = secrets.token_urlsafe(32)
        
        if expires_delta:
            expire = datetime.now(timezone.utc).replace(tzinfo=None) + expires_delta
        else:
            expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        
        payload = {
            "sub": user_id,  # subject
            "jti": jti,      # JWT ID for revocation
            "sid": session_id,  # session ID
            "exp": expire,
            "iat": datetime.now(timezone.utc).replace(tzinfo=None),  # issued at
            "type": "access"
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token, jti
    
    def create_refresh_token(self, user_id: str, session_id: str) -> Tuple[str, str]:
        """Create JWT refresh token."""
        jti = secrets.token_urlsafe(32)
        
        expire = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        
        payload = {
            "sub": user_id,
            "jti": jti,
            "sid": session_id,
            "exp": expire,
            "iat": datetime.now(timezone.utc).replace(tzinfo=None),
            "type": "refresh"
        }
        
        token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
        return token, jti
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            return payload
            
        except JWTError:
            return None
    
    def authenticate_user(
        self,
        db: Session,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Authenticate user and create session.
        
        Returns:
            Dict with user, access_token, refresh_token or None
        """
        # Find user
        user = db.query(User).filter(
            (User.username == username) | (User.email == username)
        ).first()
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        # Verify password
        if not user.verify_password(password):
            # Failed login attempt
            self.audit.log(
                action="login_failed",
                user=username,
                resource_type="user",
                resource_id=user.id,
                details={"reason": "invalid_password", "ip": ip_address}
            )
            return None
        
        # Create session
        session = UserSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            access_token_jti="",  # Will be set after token creation
            refresh_token_jti="",
            expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.add(session)
        db.flush()  # Get session ID
        
        # Create tokens
        access_token, access_jti = self.create_access_token(user.id, session.id)
        refresh_token, refresh_jti = self.create_refresh_token(user.id, session.id)
        
        # Update session with JTIs
        session.access_token_jti = access_jti
        session.refresh_token_jti = refresh_jti
        
        # Update user
        user.last_login = datetime.now(timezone.utc).replace(tzinfo=None)
        user.login_count += 1
        
        db.commit()
        
        # Audit log
        self.audit.log(
            action="login_success",
            user=user.username,
            resource_type="user",
            resource_id=user.id,
            details={"session_id": session.id, "ip": ip_address}
        )
        
        return {
            "user": user.to_dict(),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def refresh_access_token(
        self,
        db: Session,
        refresh_token: str
    ) -> Optional[Dict[str, Any]]:
        """Refresh access token using refresh token."""
        # Verify refresh token
        payload = self.verify_token(refresh_token, "refresh")
        if not payload:
            return None
        
        # Find session
        session = db.query(UserSession).filter(
            UserSession.refresh_token_jti == payload["jti"],
            UserSession.is_active == True
        ).first()
        
        if not session or not session.is_valid():
            return None
        
        # Create new access token
        access_token, access_jti = self.create_access_token(
            session.user_id,
            session.id
        )
        
        # Update session
        session.access_token_jti = access_jti
        session.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
        }
    
    def logout(self, db: Session, token: str) -> bool:
        """Logout user by revoking session."""
        payload = self.verify_token(token)
        if not payload:
            return False
        
        # Find and revoke session
        session = db.query(UserSession).filter(
            UserSession.access_token_jti == payload["jti"]
        ).first()
        
        if session:
            session.revoke()
            db.commit()
            
            # Audit log
            self.audit.log(
                action="logout",
                user=session.user.username if session.user else "unknown",
                resource_type="session",
                resource_id=session.id
            )
            return True
        
        return False
    
    def get_current_user(
        self,
        db: Session,
        token: str
    ) -> Optional[User]:
        """Get current user from token."""
        payload = self.verify_token(token)
        if not payload:
            return None
        
        # Check if session is still valid
        session = db.query(UserSession).filter(
            UserSession.access_token_jti == payload["jti"],
            UserSession.is_active == True
        ).first()
        
        if not session or not session.is_valid():
            return None
        
        # Update last used
        session.last_used_at = datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        
        return session.user
    
    def require_permission(self, permission: str):
        """Decorator/FastAPI dependency to require permission."""
        def checker(
            credentials: HTTPAuthorizationCredentials = Depends(security),
            db: Session = Depends(get_db)
        ):
            if not credentials:
                raise HTTPException(status_code=401, detail="Not authenticated")
            
            user = self.get_current_user(db, credentials.credentials)
            if not user:
                raise HTTPException(status_code=401, detail="Invalid token")
            
            if not user.has_permission(permission):
                raise HTTPException(status_code=403, detail="Permission denied")
            
            return user
        
        return checker


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get auth service singleton."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


# FastAPI dependencies

def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """FastAPI dependency to get current user."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    auth_service = get_auth_service()
    user = auth_service.get_current_user(db, credentials.credentials)
    
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user_dependency)
) -> User:
    """FastAPI dependency to get current active user."""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    
    return current_user


# Permission-based dependencies
def require_permission(permission: str):
    """Create dependency for specific permission."""
    def checker(
        current_user: User = Depends(get_current_active_user)
    ) -> User:
        if not current_user.has_permission(permission):
            raise HTTPException(
                status_code=403,
                detail=f"Permission denied: {permission}"
            )
        return current_user
    return checker


# Common permission shortcuts
require_inspect = require_permission("inspect")
require_view_history = require_permission("view_history")
require_configure = require_permission("configure")
require_manage_users = require_permission("manage_users")
