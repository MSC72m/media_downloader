"""Pydantic models for Instagram authentication."""
from pydantic import BaseModel, Field, SecretStr
from typing import Optional


class InstagramAuthState(BaseModel):
    """Authentication state for Instagram."""
    is_authenticated: bool = Field(default=False)
    username: Optional[str] = Field(default=None)
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True


class InstagramCredentials(BaseModel):
    """Credentials for Instagram authentication."""
    username: str
    password: SecretStr
    remember: bool = Field(default=False)
    
    class Config:
        """Pydantic model configuration."""
        validate_assignment = True 