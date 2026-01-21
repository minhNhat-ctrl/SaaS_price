"""Placeholder serializers/DTOs for Accounts API adapters."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class UpdateProfileRequestDTO:
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
class UpdatePreferencesRequestDTO:
    theme: Optional[str] = None
    language: Optional[str] = None
    timezone: Optional[str] = None
    date_format: Optional[str] = None
    time_format: Optional[str] = None
    sidebar_collapsed: Optional[bool] = None
    compact_mode: Optional[bool] = None
    items_per_page: Optional[int] = None
    default_view: Optional[str] = None
    show_onboarding: Optional[bool] = None
    enable_animations: Optional[bool] = None
    enable_sound: Optional[bool] = None
