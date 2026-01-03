"""
Django ORM Implementations of Products Repositories

Concrete implementations using Django ORM with sync_to_async.
⚠️ Tenant products in TENANT schema, Shared products in PUBLIC schema
"""
from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from asgiref.sync import sync_to_async
from django_tenants.utils import get_public_schema_name, schema_context
from django.db.models import Count

from services.products.domain import (
    TenantProduct,
    SharedProduct,
    SharedProductURL,
    SharedPriceHistory,
    TenantProductURLTracking,
)
from services.products.repositories.product_repo import (
    TenantProductRepository,
    SharedProductRepository,
    SharedProductURLRepository,
    TenantProductURLTrackingRepository,
    SharedPriceHistoryRepository,
)
from services.products.infrastructure.django_models import (
    TenantProduct as TenantProductModel,
    SharedProduct as SharedProductModel,
    SharedProductURL as SharedProductURLModel,
    TenantProductURLTracking as TenantProductURLTrackingModel,
    SharedPriceHistory as SharedPriceHistoryModel,
)


class DjangoTenantProductRepository(TenantProductRepository):
    """Django ORM implementation - Tenant products in tenant schema"""
    
    def _model_to_entity(self, model: TenantProductModel) -> TenantProduct:
        """Convert Django model to domain entity"""
        return TenantProduct(
            id=model.id,
            tenant_id=model.tenant_id,
            name=model.name,
            internal_code=model.internal_code,
            sku=model.sku,
            barcode=model.barcode,
            qr_code=model.qr_code,
            gtin=model.gtin,
            brand=model.brand,
            category=model.category,
            status=model.status,
            shared_product_id=model.shared_product_id,
            custom_attributes=model.custom_attributes or {},
            is_public=model.is_public,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, product: TenantProduct) -> TenantProduct:
        """Create product in tenant schema"""
        @sync_to_async
        def _create():
            model = TenantProductModel.objects.create(
                id=product.id,
                tenant_id=product.tenant_id,
                name=product.name,
                internal_code=product.internal_code,
                sku=product.sku,
                barcode=product.barcode,
                qr_code=product.qr_code,
                gtin=product.gtin,
                brand=product.brand,
                category=product.category,
                status=product.status,
                shared_product_id=product.shared_product_id,
                custom_attributes=product.custom_attributes,
                is_public=product.is_public,
            )
            return self._model_to_entity(model)
        
        return await _create()
    
    async def get_by_id(self, product_id: UUID, tenant_id: UUID) -> Optional[TenantProduct]:
        """Get product by ID in tenant"""
        @sync_to_async
        def _get():
            try:
                model = TenantProductModel.objects.get(id=product_id, tenant_id=tenant_id)
                return self._model_to_entity(model)
            except TenantProductModel.DoesNotExist:
                return None
        
        return await _get()
    
    async def get_by_sku(self, sku: str, tenant_id: UUID) -> Optional[TenantProduct]:
        """Get product by SKU in tenant"""
        @sync_to_async
        def _get():
            try:
                model = TenantProductModel.objects.get(sku=sku, tenant_id=tenant_id)
                return self._model_to_entity(model)
            except TenantProductModel.DoesNotExist:
                return None
        
        return await _get()
    
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[TenantProduct]:
        """List products for tenant"""
        @sync_to_async
        def _list():
            queryset = TenantProductModel.objects.filter(tenant_id=tenant_id)
            if status:
                queryset = queryset.filter(status=status)
            return [self._model_to_entity(m) for m in queryset[offset:offset+limit]]
        
        return await _list()
    
    async def update(self, product: TenantProduct) -> TenantProduct:
        """Update product"""
        @sync_to_async
        def _update():
            model = TenantProductModel.objects.get(id=product.id)
            model.name = product.name
            model.internal_code = product.internal_code
            model.sku = product.sku
            model.barcode = product.barcode
            model.gtin = product.gtin
            model.brand = product.brand
            model.category = product.category
            model.status = product.status
            model.shared_product_id = product.shared_product_id
            model.custom_attributes = product.custom_attributes
            model.is_public = product.is_public
            model.save()
            return self._model_to_entity(model)
        
        return await _update()
    
    async def delete(self, product_id: UUID, tenant_id: UUID) -> bool:
        """Delete product"""
        @sync_to_async
        def _delete():
            try:
                TenantProductModel.objects.filter(id=product_id, tenant_id=tenant_id).delete()
                return True
            except Exception:
                return False
        
        return await _delete()
    
    async def search(
        self,
        tenant_id: UUID,
        query: str,
        limit: int = 50
    ) -> List[TenantProduct]:
        """Search products by name, SKU, barcode"""
        @sync_to_async
        def _search():
            from django.db.models import Q
            queryset = TenantProductModel.objects.filter(
                tenant_id=tenant_id
            ).filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(barcode__icontains=query) |
                Q(internal_code__icontains=query)
            )[:limit]
            return [self._model_to_entity(m) for m in queryset]
        
        return await _search()


class DjangoSharedProductRepository(SharedProductRepository):
    """Django ORM implementation - Shared products in public schema"""
    
    def _model_to_entity(self, model: SharedProductModel) -> SharedProduct:
        """Convert Django model to domain entity"""
        return SharedProduct(
            id=model.id,
            gtin=model.gtin,
            ean=model.ean,
            upc=model.upc,
            manufacturer=model.manufacturer,
            normalized_name=model.normalized_name,
            specs_hash=model.specs_hash,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, product: SharedProduct) -> SharedProduct:
        """Create shared product in public schema"""
        @sync_to_async
        def _create():
            with schema_context(get_public_schema_name()):
                model = SharedProductModel.objects.create(
                    id=product.id,
                    gtin=product.gtin,
                    ean=product.ean,
                    upc=product.upc,
                    manufacturer=product.manufacturer,
                    normalized_name=product.normalized_name,
                    specs_hash=product.specs_hash,
                )
                return self._model_to_entity(model)
        
        return await _create()
    
    async def get_by_id(self, product_id: UUID) -> Optional[SharedProduct]:
        """Get shared product by ID"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = SharedProductModel.objects.get(id=product_id)
                    return self._model_to_entity(model)
                except SharedProductModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def get_by_gtin(self, gtin: str) -> Optional[SharedProduct]:
        """Get shared product by GTIN"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = SharedProductModel.objects.get(gtin=gtin)
                    return self._model_to_entity(model)
                except SharedProductModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def update(self, product: SharedProduct) -> SharedProduct:
        """Update shared product"""
        @sync_to_async
        def _update():
            with schema_context(get_public_schema_name()):
                model = SharedProductModel.objects.get(id=product.id)
                model.gtin = product.gtin
                model.ean = product.ean
                model.upc = product.upc
                model.manufacturer = product.manufacturer
                model.normalized_name = product.normalized_name
                model.specs_hash = product.specs_hash
                model.save()
                return self._model_to_entity(model)
        
        return await _update()
    
    async def find_or_create_by_identifiers(
        self,
        gtin: str = "",
        ean: str = "",
        upc: str = "",
        manufacturer: str = "",
        normalized_name: str = ""
    ) -> SharedProduct:
        """Find existing or create new shared product"""
        @sync_to_async
        def _find_or_create():
            with schema_context(get_public_schema_name()):
                # Try to find by GTIN
                if gtin:
                    try:
                        model = SharedProductModel.objects.get(gtin=gtin)
                        return self._model_to_entity(model)
                    except SharedProductModel.DoesNotExist:
                        pass
                
                # Create new
                from uuid import uuid4
                model = SharedProductModel.objects.create(
                    id=uuid4(),
                    gtin=gtin,
                    ean=ean,
                    upc=upc,
                    manufacturer=manufacturer,
                    normalized_name=normalized_name,
                    specs_hash="",
                )
                return self._model_to_entity(model)
        
        return await _find_or_create()
    
    async def list_all(self, limit: int = 100, offset: int = 0) -> list:
        """List all shared products"""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                models = SharedProductModel.objects.all()[offset:offset+limit]
                return [self._model_to_entity(m) for m in models]
        
        return await _list()


class DjangoSharedProductURLRepository(SharedProductURLRepository):
    """Django ORM implementation - Product URLs in public schema"""
    
    def _model_to_entity(self, model: SharedProductURLModel) -> SharedProductURL:
        """Convert Django model to domain entity"""
        return SharedProductURL(
            id=model.id,
            product_id=model.product_id,
            domain=model.domain,
            full_url=model.full_url,
            marketplace_type=model.marketplace_type,
            currency=model.currency,
            is_active=model.is_active,
            meta=model.meta or {},
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, url: SharedProductURL) -> SharedProductURL:
        """Create product URL"""
        @sync_to_async
        def _create():
            with schema_context(get_public_schema_name()):
                # Create URL without url_hash (column not available in public schema yet)
                model = SharedProductURLModel.objects.create(
                    id=url.id,
                    product_id=url.product_id,
                    domain=url.domain,
                    full_url=url.full_url,
                    marketplace_type=url.marketplace_type,
                    currency=url.currency,
                    is_active=url.is_active,
                    meta=url.meta,
                )
                return self._model_to_entity(model)
        
        return await _create()
    
    async def get_by_id(self, url_id: UUID) -> Optional[SharedProductURL]:
        """Get URL by ID"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = SharedProductURLModel.objects.get(id=url_id)
                    return self._model_to_entity(model)
                except SharedProductURLModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def get_by_url(self, full_url: str) -> Optional[SharedProductURL]:
        """Get URL by full URL string (using url_hash for case-insensitive duplicate check if available, else full_url)"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    # Try to use url_hash if column exists
                    try:
                        url_hash = SharedProductURLModel.hash_url(full_url)
                        model = SharedProductURLModel.objects.get(url_hash=url_hash)
                        return self._model_to_entity(model)
                    except:
                        # If url_hash doesn't work, fall back to exact full_url match
                        model = SharedProductURLModel.objects.get(full_url=full_url)
                        return self._model_to_entity(model)
                except SharedProductURLModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def list_by_product(self, product_id: UUID, is_active: Optional[bool] = None) -> list:
        """List URLs for product"""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                queryset = SharedProductURLModel.objects.filter(product_id=product_id)
                if is_active is not None:
                    queryset = queryset.filter(is_active=is_active)
                return [self._model_to_entity(m) for m in queryset]
        
        return await _list()
    
    async def list_by_marketplace(self, marketplace_type: str, is_active: bool = True, limit: int = 100) -> list:
        """List URLs by marketplace"""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                models = SharedProductURLModel.objects.filter(
                    marketplace_type=marketplace_type,
                    is_active=is_active
                )[:limit]
                return [self._model_to_entity(m) for m in models]
        
        return await _list()
    
    async def update(self, url: SharedProductURL) -> SharedProductURL:
        """Update URL"""
        @sync_to_async
        def _update():
            with schema_context(get_public_schema_name()):
                model = SharedProductURLModel.objects.get(id=url.id)
                model.domain = url.domain
                model.full_url = url.full_url
                model.marketplace_type = url.marketplace_type
                model.currency = url.currency
                model.is_active = url.is_active
                model.meta = url.meta
                model.save()
                return self._model_to_entity(model)
        
        return await _update()
    
    async def delete(self, url_id: UUID) -> bool:
        """Delete URL"""
        @sync_to_async
        def _delete():
            with schema_context(get_public_schema_name()):
                try:
                    SharedProductURLModel.objects.filter(id=url_id).delete()
                    return True
                except Exception:
                    return False
        
        return await _delete()


class DjangoSharedPriceHistoryRepository(SharedPriceHistoryRepository):
    """Django ORM implementation - Price history in public schema"""
    
    def _model_to_entity(self, model: SharedPriceHistoryModel) -> SharedPriceHistory:
        """Convert Django model to domain entity"""
        return SharedPriceHistory(
            id=model.id,
            product_url_id=model.product_url_id,
            price=model.price,
            currency=model.currency,
            recorded_at=model.recorded_at,
            source=model.source,
            meta=model.meta or {},
        )
    
    async def create(self, record: SharedPriceHistory) -> SharedPriceHistory:
        """Record price"""
        @sync_to_async
        def _create():
            with schema_context(get_public_schema_name()):
                model = SharedPriceHistoryModel.objects.create(
                    id=record.id,
                    product_url_id=record.product_url_id,
                    price=record.price,
                    currency=record.currency,
                    recorded_at=record.recorded_at,
                    source=record.source,
                    meta=record.meta,
                )
                return self._model_to_entity(model)
        
        return await _create()
    
    async def bulk_create(self, price_records: list) -> list:
        """Bulk create price records"""
        @sync_to_async
        def _bulk_create():
            with schema_context(get_public_schema_name()):
                models = [
                    SharedPriceHistoryModel(
                        id=record.id,
                        product_url_id=record.product_url_id,
                        price=record.price,
                        currency=record.currency,
                        recorded_at=record.recorded_at,
                        source=record.source,
                        meta=record.meta,
                    )
                    for record in price_records
                ]
                SharedPriceHistoryModel.objects.bulk_create(models)
                return [self._model_to_entity(m) for m in models]
        
        return await _bulk_create()
    
    async def get_latest_price(self, product_url_id: UUID) -> Optional[SharedPriceHistory]:
        """Get latest price for URL"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                try:
                    model = SharedPriceHistoryModel.objects.filter(
                        product_url_id=product_url_id
                    ).latest('recorded_at')
                    return self._model_to_entity(model)
                except SharedPriceHistoryModel.DoesNotExist:
                    return None
        
        return await _get()
    
    async def list_by_url(self, url_id: UUID, days: int = 30, limit: int = 100) -> list:
        """Get price history for URL"""
        @sync_to_async
        def _list():
            with schema_context(get_public_schema_name()):
                cutoff = datetime.utcnow() - timedelta(days=days)
                models = SharedPriceHistoryModel.objects.filter(
                    product_url_id=url_id,
                    recorded_at__gte=cutoff
                ).order_by('-recorded_at')[:limit]
                return [self._model_to_entity(m) for m in models]
        
        return await _list()
    
    async def get_price_history(
        self,
        product_url_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 1000
    ) -> list:
        """Get price history for URL with date range"""
        @sync_to_async
        def _get():
            with schema_context(get_public_schema_name()):
                queryset = SharedPriceHistoryModel.objects.filter(product_url_id=product_url_id)
                if start_date:
                    queryset = queryset.filter(recorded_at__gte=start_date)
                if end_date:
                    queryset = queryset.filter(recorded_at__lte=end_date)
                models = queryset.order_by('-recorded_at')[:limit]
                return [self._model_to_entity(m) for m in models]
        
        return await _get()
    
    async def get_average_price(self, product_url_id: UUID, days: int = 30) -> Optional[float]:
        """Calculate average price over period"""
        @sync_to_async
        def _calc():
            from django.db.models import Avg
            with schema_context(get_public_schema_name()):
                cutoff = datetime.utcnow() - timedelta(days=days)
                result = SharedPriceHistoryModel.objects.filter(
                    product_url_id=product_url_id,
                    recorded_at__gte=cutoff
                ).aggregate(avg_price=Avg('price'))
                return result['avg_price']
        
        return await _calc()
    
    async def get_price_trend(self, product_url_id: UUID, days: int = 30) -> dict:
        """Get price trend statistics"""
        @sync_to_async
        def _trend():
            from django.db.models import Min, Max, Avg
            with schema_context(get_public_schema_name()):
                cutoff = datetime.utcnow() - timedelta(days=days)
                result = SharedPriceHistoryModel.objects.filter(
                    product_url_id=product_url_id,
                    recorded_at__gte=cutoff
                ).aggregate(
                    min_price=Min('price'),
                    max_price=Max('price'),
                    avg_price=Avg('price'),
                    count=Count('id')
                )
                
                # Get latest price
                latest = SharedPriceHistoryModel.objects.filter(
                    product_url_id=product_url_id
                ).latest('recorded_at')
                
                return {
                    'min_price': result['min_price'],
                    'max_price': result['max_price'],
                    'avg_price': result['avg_price'],
                    'current_price': latest.price if latest else None,
                    'count': result['count'],
                    'currency': latest.currency if latest else 'USD',
                }
        
        return await _trend()


class DjangoTenantProductURLTrackingRepository(TenantProductURLTrackingRepository):
    """Django ORM implementation - Tenant URL tracking in tenant schema"""
    
    def _set_tenant_schema(self, tenant_id: UUID):
        """Set database connection to tenant schema"""
        from django.db import connection
        from core.tenants.infrastructure.django_models import Tenant
        
        try:
            tenant = Tenant.objects.get(id=tenant_id)
            connection.set_tenant(tenant)
        except Tenant.DoesNotExist:
            pass  # Will fail on query if tenant doesn't exist
    
    def _model_to_entity(self, model: TenantProductURLTrackingModel) -> TenantProductURLTracking:
        """Convert Django model to domain entity"""
        return TenantProductURLTracking(
            id=model.id,
            tenant_id=model.tenant_id,
            product_id=model.product_id,
            shared_url_id=model.shared_url_id,
            custom_label=model.custom_label,
            is_primary=model.is_primary,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    async def create(self, tracking: TenantProductURLTracking) -> TenantProductURLTracking:
        """Create new URL tracking record"""
        @sync_to_async
        def _create():
            self._set_tenant_schema(tracking.tenant_id)
            model = TenantProductURLTrackingModel.objects.create(
                id=tracking.id,
                tenant_id=tracking.tenant_id,
                product_id=tracking.product_id,
                shared_url_id=tracking.shared_url_id,
                custom_label=tracking.custom_label,
                is_primary=tracking.is_primary,
            )
            return self._model_to_entity(model)
        
        return await _create()
    
    async def get_by_id(self, tracking_id: UUID, tenant_id: UUID) -> Optional[TenantProductURLTracking]:
        """Get tracking by ID"""
        @sync_to_async
        def _get():
            self._set_tenant_schema(tenant_id)
            try:
                model = TenantProductURLTrackingModel.objects.get(
                    id=tracking_id,
                    tenant_id=tenant_id
                )
                return self._model_to_entity(model)
            except TenantProductURLTrackingModel.DoesNotExist:
                return None
        
        return await _get()
    
    async def get_by_tenant_and_url(
        self,
        tenant_id: UUID,
        shared_url_id: UUID
    ) -> Optional[TenantProductURLTracking]:
        """Get tracking by tenant and shared URL"""
        @sync_to_async
        def _get():
            self._set_tenant_schema(tenant_id)
            try:
                model = TenantProductURLTrackingModel.objects.get(
                    tenant_id=tenant_id,
                    shared_url_id=shared_url_id
                )
                return self._model_to_entity(model)
            except TenantProductURLTrackingModel.DoesNotExist:
                return None
        
        return await _get()
    
    async def list_by_product(
        self,
        product_id: UUID,
        tenant_id: UUID
    ) -> List[TenantProductURLTracking]:
        """List all URLs tracked by tenant product"""
        @sync_to_async
        def _list():
            self._set_tenant_schema(tenant_id)
            models = TenantProductURLTrackingModel.objects.filter(
                product_id=product_id,
                tenant_id=tenant_id
            ).order_by('-is_primary', '-created_at')
            return [self._model_to_entity(m) for m in models]
        
        return await _list()
    
    async def list_by_tenant(self, tenant_id: UUID) -> List[TenantProductURLTracking]:
        """List all URLs tracked by tenant"""
        @sync_to_async
        def _list():
            self._set_tenant_schema(tenant_id)
            models = TenantProductURLTrackingModel.objects.filter(
                tenant_id=tenant_id
            ).order_by('-created_at')
            return [self._model_to_entity(m) for m in models]
        
        return await _list()
    
    async def delete(self, tracking_id: UUID, tenant_id: UUID) -> bool:
        """Delete tracking record"""
        @sync_to_async
        def _delete():
            self._set_tenant_schema(tenant_id)
            deleted_count, _ = TenantProductURLTrackingModel.objects.filter(
                id=tracking_id,
                tenant_id=tenant_id
            ).delete()
            return deleted_count > 0
        
        return await _delete()
