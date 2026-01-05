"""
API Views

Thin controllers - validate input, call services, return responses.
Based on PRODUCTS_DATA_CONTRACT.md architecture.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from uuid import UUID
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


def get_tenant_id(request, tenant_id_from_url=None):
    """
    Get tenant_id from various sources (priority order):
    1. URL path parameter (tenant_id_from_url)
    2. request.tenant (from middleware)
    3. Query params (?tenant_id=xxx)
    4. Request body (for POST/PUT/PATCH)
    """
    # 1. From URL path
    if tenant_id_from_url:
        return UUID(str(tenant_id_from_url))
    
    # 2. From middleware
    if hasattr(request, 'tenant') and request.tenant:
        return UUID(str(request.tenant.id))
    
    # 3. From query params
    tenant_id = request.query_params.get('tenant_id')
    if tenant_id:
        return UUID(tenant_id)
    
    # 4. From request body
    if hasattr(request, 'data') and request.data:
        tenant_id = request.data.get('tenant_id')
        if tenant_id:
            return UUID(str(tenant_id))
    
    return None


from services.products.domain import (
    ProductDomainError,
    ProductNotFoundError,
    DuplicateSKUError,
    DuplicateGTINError,
    DuplicateURLError,
    URLMappingNotFoundError,
    InvalidURLError,
)
from services.products.services.use_cases import ProductService, PriceService
from services.products.infrastructure.django_repository import (
    DjangoProductRepository,
    DjangoProductURLMappingRepository,
)
from services.products_shared.infrastructure.django_repository import (
    DjangoProductURLRepository,
    DjangoPriceHistoryRepository,
    DjangoDomainRepository,
)
from services.products.api.serializers import (
    ProductSerializer,
    ProductCreateSerializer,
    ProductUpdateSerializer,
    AddURLToProductSerializer,
    ProductURLSerializer,
    ProductURLMappingSerializer,
    PriceHistorySerializer,
)


# ============================================================
# Service Factory
# ============================================================

def get_product_service(tenant_id: UUID = None) -> ProductService:
    """Factory to create ProductService with dependencies."""
    return ProductService(
        product_repo=DjangoProductRepository(),
        mapping_repo=DjangoProductURLMappingRepository(tenant_id=tenant_id),
        url_repo=DjangoProductURLRepository(),  # Shared (public schema)
        domain_repo=DjangoDomainRepository(),  # Shared (public schema)
    )


def get_price_service() -> PriceService:
    """Factory to create PriceService with dependencies."""
    return PriceService(
        price_history_repo=DjangoPriceHistoryRepository(),
        url_repo=DjangoProductURLRepository(),
    )


# ============================================================
# Product API Views
# ============================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProductListCreateView(APIView):
    """
    List products or create a new product.
    
    GET /api/products/?tenant_id=<uuid>
    POST /api/products/
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, tenant_id=None):
        """List products for current tenant."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Get query parameters
        status_filter = request.query_params.get('status')
        limit = int(request.query_params.get('limit', 100))
        offset = int(request.query_params.get('offset', 0))
        
        # Call service
        service = get_product_service(tid)
        products = service.list_products(tid, status_filter, limit, offset)
        
        # Serialize and return
        serializer = ProductSerializer(products, many=True)
        return Response({
            'success': True,
            'data': serializer.data,
            'count': len(products),
        })
    
    def post(self, request, tenant_id=None):
        """Create a new product."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate input
        serializer = ProductCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Call service
        try:
            service = get_product_service(tid)
            product = service.create_product(
                tenant_id=tid,
                **serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': ProductSerializer(product).data,
            }, status=status.HTTP_201_CREATED)
            
        except (DuplicateSKUError, DuplicateGTINError) as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class ProductDetailView(APIView):
    """
    Retrieve, update, or delete a product.
    
    GET /api/products/<id>/?tenant_id=<uuid>
    PUT /api/products/<id>/
    PATCH /api/products/<id>/
    DELETE /api/products/<id>/
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, product_id, tenant_id=None):
        """Get product details."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_product_service(tid)
        product = service.get_product(product_id, tid)
        
        if not product:
            return Response({
                'success': False,
                'error': 'Product not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'data': ProductSerializer(product).data,
        })
    
    def put(self, request, product_id, tenant_id=None):
        """Update product (full update)."""
        return self._update(request, product_id, tenant_id, partial=False)
    
    def patch(self, request, product_id, tenant_id=None):
        """Update product (partial update)."""
        return self._update(request, product_id, tenant_id, partial=True)
    
    def _update(self, request, product_id, tenant_id=None, partial=True):
        """Internal update method."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate input
        serializer = ProductUpdateSerializer(data=request.data, partial=partial)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Call service
        try:
            service = get_product_service(tid)
            product = service.update_product(
                product_id=product_id,
                tenant_id=tid,
                **serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': ProductSerializer(product).data,
            })
            
        except ProductNotFoundError as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_404_NOT_FOUND)
            
        except (DuplicateSKUError, DuplicateGTINError) as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, product_id, tenant_id=None):
        """Delete product."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_product_service(tid)
        deleted = service.delete_product(product_id, tid)
        
        if not deleted:
            return Response({
                'success': False,
                'error': 'Product not found',
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'message': 'Product deleted successfully',
        })


# ============================================================
# Product URL API Views
# ============================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProductURLsView(APIView):
    """
    Manage URLs for a product.
    
    GET /api/products/<id>/urls/?tenant_id=<uuid>
    POST /api/products/<id>/urls/
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, product_id, tenant_id=None):
        """Get all URLs for a product."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_product_service(tid)
        url_infos = service.get_product_urls(tid, product_id)
        
        # Format response
        urls = []
        for url_info in url_infos:
            urls.append({
                'mapping': ProductURLMappingSerializer(url_info.mapping).data,
                'url': ProductURLSerializer(url_info.url).data,
            })
        
        return Response({
            'success': True,
            'data': urls,
        })
    
    def post(self, request, product_id, tenant_id=None):
        """Add URL to product."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Validate input
        serializer = AddURLToProductSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                'success': False,
                'errors': serializer.errors,
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Call service
        try:
            service = get_product_service(tid)
            url_info = service.add_url_to_product(
                tenant_id=tid,
                product_id=product_id,
                **serializer.validated_data
            )
            
            return Response({
                'success': True,
                'data': {
                    'mapping': ProductURLMappingSerializer(url_info.mapping).data,
                    'url': ProductURLSerializer(url_info.url).data,
                },
            }, status=status.HTTP_201_CREATED)
            
        except ProductNotFoundError as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_404_NOT_FOUND)
            
        except DuplicateURLError as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)
            
        except InvalidURLError as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_exempt, name='dispatch')
class ProductURLDetailView(APIView):
    """
    Remove URL from product.
    
    DELETE /api/products/<product_id>/urls/<url_hash>/?tenant_id=<uuid>
    
    Note: Uses url_hash instead of url_id for cross-schema safety.
    """
    authentication_classes = []
    permission_classes = []
    
    def delete(self, request, product_id, url_hash, tenant_id=None):
        """Remove URL from product by url_hash."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            service = get_product_service(tid)
            deleted = service.remove_url_from_product(
                tenant_id=tid,
                product_id=product_id,
                url_hash=url_hash,
            )
            
            if not deleted:
                return Response({
                    'success': False,
                    'error': 'URL mapping not found',
                }, status=status.HTTP_404_NOT_FOUND)
            
            return Response({
                'success': True,
                'message': 'URL removed from product successfully',
            })
            
        except URLMappingNotFoundError as e:
            return Response({
                'success': False,
                'error': str(e),
            }, status=status.HTTP_404_NOT_FOUND)


# ============================================================
# Search API Views
# ============================================================

@method_decorator(csrf_exempt, name='dispatch')
class ProductSearchView(APIView):
    """
    Search products.
    
    GET /api/products/search/?q=<query>&tenant_id=<uuid>
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, tenant_id=None):
        """Search products."""
        tid = get_tenant_id(request, tenant_id)
        if not tid:
            return Response({
                'success': False,
                'error': 'tenant_id is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        query = request.query_params.get('q', '')
        limit = int(request.query_params.get('limit', 50))
        
        if not query:
            return Response({
                'success': False,
                'error': 'Query parameter "q" is required',
            }, status=status.HTTP_400_BAD_REQUEST)
        
        service = get_product_service(tid)
        products = service.search_products(tid, query, limit)
        
        return Response({
            'success': True,
            'data': ProductSerializer(products, many=True).data,
            'count': len(products),
        })


# ============================================================
# Price History API Views
# ============================================================

@method_decorator(csrf_exempt, name='dispatch')
class PriceHistoryView(APIView):
    """
    Get price history for a URL.
    
    GET /api/urls/<url_hash>/price-history/
    """
    authentication_classes = []
    permission_classes = []
    
    def get(self, request, url_hash):
        """Get price history for a URL by hash."""
        service = get_price_service()
        
        days = int(request.query_params.get('days', 30))
        price_history = service.get_price_trend(url_hash, days)
        
        return Response({
            'success': True,
            'data': PriceHistorySerializer(price_history, many=True).data,
        })
