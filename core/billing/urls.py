"""
URL configuration for Billing module (Contract-Centric).

Routes for billing-related API endpoints:
- Contracts management
- Webhooks for payment gateways
- Payment tracking
"""
from django.urls import path, include

app_name = 'billing'

urlpatterns = [
    # Placeholder for future API endpoints
    # POST   /api/billing/contracts/            - Create contract
    # GET    /api/billing/contracts/{id}/       - Retrieve contract
    # GET    /api/billing/contracts/            - List contracts
    # POST   /api/billing/webhooks/stripe/      - Stripe webhook handler
    # POST   /api/billing/webhooks/payos/       - PayOS webhook handler
    # POST   /api/billing/webhooks/vnpay/       - VNPay webhook handler
]
