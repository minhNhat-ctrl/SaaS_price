"""
Crawl Service Module

A layered architecture module for managing product price crawling.

Architecture:
- Domain: Pure business logic (no framework dependencies)
- Repositories: Data access abstractions
- Infrastructure: Django ORM models and external integrations
- Services: Application use cases
- API: Minimal bot endpoints (pull jobs, submit results)
- Admin: Django admin interface for management

Usage:
1. Django Admin: Manage jobs, view tasks and results
2. Bot API: POST /api/crawl/bot/pull/ and /api/crawl/bot/submit/
3. Scheduler: Run via management command or Celery Beat
"""

__version__ = '1.0.0'

default_app_config = 'services.crawl_service.apps.CrawlServiceConfig'
