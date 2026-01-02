"""
Products API Views - DRF endpoints for product management.

Thin controllers - validate input, call service, format response.
"""
import json
import logging
from functools import wraps
from uuid import UUID
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from asgiref.sync import async_to_sync

from services.products.api.serializers import (
    TenantProductSerializer,
    CreateProductSerializer,
    UpdateProductSerializer,
    AddProductURLSerializer,
    RecordPriceSerializer,
    ProductURLSerializer,
    PriceRecordSerializer,
)
from services.products.services.product_service import ProductService
from services.products.repositories.product_repo import (
    TenantProductRepository,
    SharedProductRepository,
    SharedProductURLRepository,
    SharedPriceHistoryRepository,
)
from services.products.infrastructure.django_repository import (
    DjangoTenantProductRepository,
    DjangoSharedProductRepository,
    DjangoSharedProductURLRepository,
    DjangoSharedPriceHistoryRepository,
)

logger = logging.getLogger(__name__)


def login_required_api(view_func):
    """Require authentication for API endpoints"""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'error': 'Authentication required'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return wrapper


def _get_product_service() -> ProductService:
    """Factory to create ProductService with dependencies"""
    return ProductService(
        tenant_product_repo=DjangoTenantProductRepository(),
        shared_product_repo=DjangoSharedProductRepository(),
        product_url_repo=DjangoSharedProductURLRepository(),
        price_history_repo=DjangoSharedPriceHistoryRepository(),
    )


def _parse_json_body(request):
    """Parse JSON body from request"""
    try:
        return json.loads(request.body.decode('utf-8'))
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        raise ValueError(f"Invalid JSON body: {str(e)}")


def _product_to_dict(product):
    """Convert product entity to dict for response"""
    return {
        'id': str(product.id),
        'tenant_id': str(product.tenant_id),
        'name': product.name,
        'sku': product.sku,
        'internal_code': product.internal_code,
        'barcode': product.barcode,
        'gtin': product.gtin,
        'brand': product.brand,
        'category': product.category,
        'status': product.status,
        'shared_product_id': str(product.shared_product_id) if product.shared_product_id else None,
        'custom_attributes': product.custom_attributes,
        'is_public': product.is_public,
        'created_at': product.created_at.isoformat() if product.created_at else None,
        'updated_at': product.updated_at.isoformat() if product.updated_at else None,
    }


def _url_to_dict(url):
    """Convert ProductURL entity to dict"""
    return {
        'id': str(url.id),
        'product_id': str(url.product_id),
        'domain': url.domain,
        'full_url': url.full_url,
        'marketplace_type': url.marketplace_type,
        'currency': url.currency,
        'is_active': url.is_active,
        'meta': url.meta,
        'created_at': url.created_at.isoformat() if url.created_at else None,
        'updated_at': url.updated_at.isoformat() if url.updated_at else None,
    }


def _price_to_dict(price):
    """Convert PriceRecord entity to dict"""
    return {
        'id': str(price.id),
        'product_url_id': str(price.product_url_id),
        'price': price.price,
        'currency': price.currency,
        'source': price.source,
        'recorded_at': price.recorded_at.isoformat() if price.recorded_at else None,
        'meta': price.meta,
    }


# ============================================================
# Tenant Product Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required_api
def products_list_create_view(request, tenant_id):
    """
    GET /api/products/tenants/{tenant_id}/products/ - List products
    POST /api/products/tenants/{tenant_id}/products/ - Create product
    """
    if request.method == "GET":
        return _list_products(request, tenant_id)
    elif request.method == "POST":
        return _create_product(request, tenant_id)


def _list_products(request, tenant_id):
    """List products for tenant"""
    try:
        status_filter = request.GET.get('status')
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        
        service = _get_product_service()
        products = async_to_sync(service.list_tenant_products)(
            tenant_id=UUID(tenant_id),
            status=status_filter,
            limit=limit,
            offset=offset
        )
        
        return JsonResponse({
            'success': True,
            'products': [_product_to_dict(p) for p in products],
            'count': len(products)
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"List products error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


def _create_product(request, tenant_id):
    """Create product for tenant"""
    try:
        data = _parse_json_body(request)
        serializer = CreateProductSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
        
        service = _get_product_service()
        product = async_to_sync(service.create_tenant_product)(
            tenant_id=UUID(tenant_id),
            **serializer.validated_data
        )
        
        return JsonResponse({
            'success': True,
            'product': _product_to_dict(product),
            'message': 'Product created successfully'
        }, status=201)
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Create product error: {str(e)}", exc_info=True)
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["GET", "PATCH", "DELETE"])
@login_required_api
def products_detail_view(request, tenant_id, product_id):
    """
    GET /api/products/tenants/{tenant_id}/products/{product_id}/ - Get product
    PATCH /api/products/tenants/{tenant_id}/products/{product_id}/ - Update product
    DELETE /api/products/tenants/{tenant_id}/products/{product_id}/ - Delete product
    """
    if request.method == "GET":
        return _get_product(request, tenant_id, product_id)
    elif request.method == "PATCH":
        return _update_product(request, tenant_id, product_id)
    elif request.method == "DELETE":
        return _delete_product(request, tenant_id, product_id)


def _get_product(request, tenant_id, product_id):
    """Get product details"""
    try:
        service = _get_product_service()
        product = async_to_sync(service.get_tenant_product)(
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id)
        )
        
        if not product:
            return JsonResponse({'success': False, 'error': 'Product not found'}, status=404)
        
        return JsonResponse({'success': True, 'product': _product_to_dict(product)})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Get product error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


def _update_product(request, tenant_id, product_id):
    """Update product"""
    try:
        data = _parse_json_body(request)
        serializer = UpdateProductSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
        
        service = _get_product_service()
        product = async_to_sync(service.update_tenant_product)(
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id),
            **serializer.validated_data
        )
        
        return JsonResponse({'success': True, 'product': _product_to_dict(product)})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Update product error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


def _delete_product(request, tenant_id, product_id):
    """Delete product"""
    try:
        service = _get_product_service()
        success = async_to_sync(service.delete_tenant_product)(
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id)
        )
        
        if not success:
            return JsonResponse({'success': False, 'error': 'Failed to delete product'}, status=400)
        
        return JsonResponse({'success': True, 'message': 'Product deleted'})
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Delete product error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


# ============================================================
# Product URL Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required_api
def product_urls_view(request, tenant_id, product_id):
    """
    GET /api/products/tenants/{tenant_id}/products/{product_id}/urls/ - List URLs
    POST /api/products/tenants/{tenant_id}/products/{product_id}/urls/ - Add URL
    """
    if request.method == "GET":
        return _list_product_urls(request, tenant_id, product_id)
    elif request.method == "POST":
        return _add_product_url(request, tenant_id, product_id)


def _list_product_urls(request, tenant_id, product_id):
    """List tracking URLs for product"""
    try:
        service = _get_product_service()
        urls = async_to_sync(service.list_product_urls)(
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id)
        )
        
        return JsonResponse({
            'success': True,
            'urls': [_url_to_dict(u) for u in urls],
            'count': len(urls)
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"List product URLs error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


def _add_product_url(request, tenant_id, product_id):
    """Add tracking URL to product"""
    try:
        data = _parse_json_body(request)
        serializer = AddProductURLSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
        
        service = _get_product_service()
        product_url = async_to_sync(service.add_product_url)(
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id),
            **serializer.validated_data
        )
        
        return JsonResponse({
            'success': True,
            'url': _url_to_dict(product_url),
            'message': 'URL added successfully'
        }, status=201)
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Add product URL error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


# ============================================================
# Price History Endpoints
# ============================================================

@csrf_exempt
@require_http_methods(["GET", "POST"])
@login_required_api
def price_history_view(request, tenant_id, product_id, url_id):
    """
    GET /api/products/tenants/{tenant_id}/products/{product_id}/urls/{url_id}/prices/ - Get history
    POST /api/products/tenants/{tenant_id}/products/{product_id}/urls/{url_id}/prices/ - Record price
    """
    if request.method == "GET":
        return _get_price_history(request, tenant_id, product_id, url_id)
    elif request.method == "POST":
        return _record_price(request, tenant_id, product_id, url_id)


def _get_price_history(request, tenant_id, product_id, url_id):
    """Get price history for URL"""
    try:
        days = int(request.GET.get('days', 30))
        limit = int(request.GET.get('limit', 100))
        
        service = _get_product_service()
        prices = async_to_sync(service.get_price_history)(
            product_url_id=UUID(url_id),
            tenant_id=UUID(tenant_id),
            days=days,
            limit=limit
        )
        
        return JsonResponse({
            'success': True,
            'prices': [_price_to_dict(p) for p in prices],
            'count': len(prices)
        })
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Get price history error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)


def _record_price(request, tenant_id, product_id, url_id):
    """Record price for product URL"""
    try:
        data = _parse_json_body(request)
        serializer = RecordPriceSerializer(data=data)
        if not serializer.is_valid():
            return JsonResponse({'success': False, 'errors': serializer.errors}, status=400)
        
        service = _get_product_service()
        price_record = async_to_sync(service.record_price)(
            product_url_id=UUID(url_id),
            product_id=UUID(product_id),
            tenant_id=UUID(tenant_id),
            **serializer.validated_data
        )
        
        return JsonResponse({
            'success': True,
            'price': _price_to_dict(price_record),
            'message': 'Price recorded'
        }, status=201)
        
    except ValueError as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)
    except Exception as e:
        logger.error(f"Record price error: {str(e)}")
        return JsonResponse({'success': False, 'error': f'Internal error: {str(e)}'}, status=500)
