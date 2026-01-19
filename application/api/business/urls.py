"""Business API URLs."""
from django.urls import path

from .create_product import CreateProductView


urlpatterns = [
    path('create-product/', CreateProductView.as_view(), name='business-create-product'),
]
