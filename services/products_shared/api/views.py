"""
API Views for Products Shared Module

Endpoints:
- GET /api/products/{product_id}/prices/
- POST /api/products/{product_id}/prices/
- GET /api/products/{product_id}/urls/
- POST /api/products/{product_id}/urls/{url_hash}
"""

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from django.utils import timezone
from decimal import Decimal
from uuid import UUID
import logging

from services.products_shared.infrastructure.django_models import (
    ProductURL,
    PriceHistory,
    Domain,
)

logger = logging.getLogger(__name__)


class ProductPriceHistoryView(APIView):
    """
    GET /api/products/{product_id}/prices/
    POST /api/products/{product_id}/prices/
    
    Manage price history for a product URL.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, product_id):
        """Get price history for product URL"""
        try:
            url_hash = request.query_params.get('url_hash')
            
            if not url_hash:
                return Response({
                    'success': False,
                    'error': 'validation_error',
                    'detail': 'url_hash parameter is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get ProductURL
            try:
                product_url = ProductURL.objects.get(url_hash=url_hash)
            except ProductURL.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'not_found',
                    'detail': f'ProductURL {url_hash} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Get price history
            prices = PriceHistory.objects.filter(
                product_url=product_url
            ).order_by('-scraped_at')
            
            # Limit
            limit = int(request.query_params.get('limit', 100))
            prices = prices[:limit]
            
            data = {
                'success': True,
                'data': {
                    'product_url': {
                        'url_hash': product_url.url_hash,
                        'normalized_url': product_url.normalized_url,
                        'domain': product_url.domain.name if product_url.domain else None,
                    },
                    'prices': [
                        {
                            'id': str(p.id),
                            'price': float(p.price),
                            'currency': p.currency,
                            'original_price': float(p.original_price) if p.original_price else None,
                            'is_available': p.is_available,
                            'stock_status': p.stock_status,
                            'source': p.source,
                            'scraped_at': p.scraped_at.isoformat(),
                            'created_at': p.created_at.isoformat(),
                        }
                        for p in prices
                    ],
                    'count': len(prices),
                }
            }
            
            return Response(data)
        
        except Exception as e:
            logger.error(f"Error getting price history: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, product_id):
        """Record new price for product URL"""
        try:
            data = request.data
            
            # Validate required fields
            required = ['url_hash', 'price', 'currency']
            for field in required:
                if field not in data:
                    return Response({
                        'success': False,
                        'error': 'validation_error',
                        'detail': f'Missing required field: {field}'
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            url_hash = data['url_hash']
            price = Decimal(str(data['price']))
            currency = data['currency']
            
            # Validate price
            if price < 0:
                return Response({
                    'success': False,
                    'error': 'validation_error',
                    'detail': 'Price must be >= 0'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get ProductURL
            try:
                product_url = ProductURL.objects.get(url_hash=url_hash)
            except ProductURL.DoesNotExist:
                return Response({
                    'success': False,
                    'error': 'not_found',
                    'detail': f'ProductURL {url_hash} not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            # Create price history record
            price_record = PriceHistory.objects.create(
                product_url=product_url,
                price=price,
                currency=currency,
                original_price=data.get('original_price'),
                is_available=data.get('is_available', True),
                stock_status=data.get('stock_status', ''),
                stock_quantity=data.get('stock_quantity'),
                source=data.get('source', 'MANUAL'),
                scraped_at=timezone.now(),
            )
            
            logger.info(
                f"Recorded price for {url_hash}: {price} {currency}"
            )
            
            return Response({
                'success': True,
                'data': {
                    'id': str(price_record.id),
                    'product_url': url_hash,
                    'price': float(price_record.price),
                    'currency': price_record.currency,
                    'is_available': price_record.is_available,
                    'source': price_record.source,
                    'scraped_at': price_record.scraped_at.isoformat(),
                }
            }, status=status.HTTP_201_CREATED)
        
        except Exception as e:
            logger.error(f"Error recording price: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProductURLView(APIView):
    """
    GET /api/products/{product_id}/urls/
    POST /api/products/{product_id}/urls/
    DELETE /api/products/{product_id}/urls/{url_hash}/
    
    Manage product URLs.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, product_id):
        """List all URLs for product"""
        try:
            # Get domain filter
            domain_name = request.query_params.get('domain')
            
            query = ProductURL.objects.select_related('domain')
            if domain_name:
                query = query.filter(domain__name=domain_name)
            
            urls = query.all()
            
            data = {
                'success': True,
                'data': {
                    'urls': [
                        {
                            'url_hash': url.url_hash,
                            'normalized_url': url.normalized_url,
                            'raw_url': url.raw_url,
                            'domain': url.domain.name if url.domain else None,
                            'is_active': url.is_active,
                            'created_at': url.created_at.isoformat(),
                        }
                        for url in urls
                    ],
                    'count': len(urls),
                }
            }
            
            return Response(data)
        
        except Exception as e:
            logger.error(f"Error listing URLs: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request, product_id):
        """Add new URL"""
        try:
            data = request.data
            
            if 'raw_url' not in data:
                return Response({
                    'success': False,
                    'error': 'validation_error',
                    'detail': 'raw_url is required'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            raw_url = data['raw_url']
            domain_name = data.get('domain', 'unknown')
            
            # Get or create domain
            domain, _ = Domain.objects.get_or_create(name=domain_name)
            
            # Create ProductURL
            # In real implementation, would use ProductURL model's create method
            from services.products_shared.infrastructure.django_models import ProductURL as ProductURLModel
            import hashlib
            
            url_hash = hashlib.sha256(raw_url.encode()).hexdigest()[:64]
            
            product_url, created = ProductURLModel.objects.get_or_create(
                url_hash=url_hash,
                defaults={
                    'raw_url': raw_url,
                    'normalized_url': raw_url,
                    'domain': domain,
                    'is_active': True,
                }
            )
            
            return Response({
                'success': True,
                'data': {
                    'url': {
                        'url_hash': product_url.url_hash,
                        'raw_url': product_url.raw_url,
                        'normalized_url': product_url.normalized_url,
                        'domain': product_url.domain.name,
                        'is_active': product_url.is_active,
                        'created': created,
                    }
                }
            }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
        
        except Exception as e:
            logger.error(f"Error creating URL: {e}", exc_info=True)
            return Response({
                'success': False,
                'error': 'internal_error',
                'detail': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
