"""DTO contracts for Accounts module interactions with application layer."""
from dataclasses import dataclass
from typing import Optional, Dict, Any
from uuid import UUID


@dataclass
class ProfileRequestContext:
    user_id: UUID
    tenant_id: Optional[UUID] = None


@dataclass
class UpdateProfileCommand:
    context: ProfileRequestContext
    display_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    bio: Optional[str] = None
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    twitter: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None


@dataclass
class UpdatePreferencesCommand:
    context: ProfileRequestContext
    preferences: Dict[str, Any]


@dataclass
class UpdateNotificationSettingsCommand:
    context: ProfileRequestContext
    channels: Dict[str, Any]


@dataclass
class UploadAvatarCommand:
    context: ProfileRequestContext
    file_name: str
    content_type: str
    file_bytes: bytes
