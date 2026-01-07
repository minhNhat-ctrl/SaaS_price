"""
Bot API URLs with State Machine

Only 2 endpoints:
- pull/: Bot pulls available PENDING jobs, acquires lock
- submit/: Bot submits crawl result, transitions state
"""

from django.urls import path
from .views import BotPullJobsView, BotSubmitResultView

app_name = 'crawl_api'

urlpatterns = [
    path('pull/', BotPullJobsView.as_view(), name='pull'),
    path('submit/', BotSubmitResultView.as_view(), name='submit'),
]
