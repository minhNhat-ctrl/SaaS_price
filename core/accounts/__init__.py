"""
Accounts Module - User Profiles & Preferences

User-centric data management including:
- User profiles (personal information)
- User preferences (settings, display options)
- Notification settings
- Avatar/photo management

Architecture:
- domain/: Pure business entities (UserProfile, Preferences, NotificationSettings)
- services/: Profile management use cases
- repositories/: Data access interfaces
- infrastructure/: Django ORM, file storage, API

Note: Completely independent from Django admin User model.
Can be tenant-aware (user profile per tenant) or global.
"""
