"""
Django Repository Implementations for Shared Data

All operations run in PUBLIC schema.
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime, timedelta
from decimal import Decimal

from django.db import transaction, models
from django_tenants.utils import get_public_schema_name, schema_context

from services.products_shared.domain.entities import (
    Domain as DomainEntity,
    ProductURL as ProductURLEntity,
    PriceHistory as PriceHistoryEntity,
)
from services.products_shared.infrastructure.django_models import (
    Domain as DomainModel,
    ProductURL as ProductURLModel,
    PriceHistory as PriceHistoryModel,
)
from services.products_shared.repositories.interfaces import (
    DomainRepository,
    ProductURLRepository,
    PriceHistoryRepository,
)


# ============================================================
# Entity-Model Mappers
# ============================================================

class DomainMapper:
    """Maps between Domain entity and Django model."""
    
    @staticmethod
    def to_entity(model: DomainModel) -> DomainEntity:
        return DomainEntity(
            id=model.id,
            name=model.name,
            crawl_enabled=model.crawl_enabled,
            crawl_interval_hours=model.crawl_interval_hours,
            rate_limit_per_minute=model.rate_limit_per_minute,
            parser_class=model.parser_class,
            parser_config=model.parser_config or {},
            is_active=model.is_active,
            last_health_check=model.last_health_check,
            health_status=model.health_status,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @staticmethod
    def to_model(entity: DomainEntity) -> DomainModel:
        return DomainModel(
            id=entity.id,
            name=entity.name,
            crawl_enabled=entity.crawl_enabled,
            crawl_interval_hours=entity.crawl_interval_hours,
            rate_limit_per_minute=entity.rate_limit_per_minute,
            parser_class=entity.parser_class,
            parser_config=entity.parser_config,
            is_active=entity.is_active,
            last_health_check=entity.last_health_check,
            health_status=entity.health_status,
        )


class ProductURLMapper:
    """Maps between ProductURL entity and Django model."""
    
    @staticmethod
    def to_entity(model: ProductURLModel) -> ProductURLEntity:
        return ProductURLEntity(
            id=model.id,
            url_hash=model.url_hash,
            raw_url=model.raw_url,
            normalized_url=model.normalized_url,
            domain_id=model.domain_id,
            reference_count=model.reference_count,
            is_active=model.is_active,
            last_crawled_at=model.last_crawled_at,
            crawl_error=model.crawl_error,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )
    
    @staticmethod
    def to_model(entity: ProductURLEntity) -> ProductURLModel:
        return ProductURLModel(
            id=entity.id,
            url_hash=entity.url_hash,
            raw_url=entity.raw_url,
            normalized_url=entity.normalized_url,
            domain_id=entity.domain_id,
            reference_count=entity.reference_count,
            is_active=entity.is_active,
            last_crawled_at=entity.last_crawled_at,
            crawl_error=entity.crawl_error,
        )


class PriceHistoryMapper:
    """Maps between PriceHistory entity and Django model."""
    
    @staticmethod
    def to_entity(model: PriceHistoryModel) -> PriceHistoryEntity:
        return PriceHistoryEntity(
            id=model.id,
            product_url_id=model.product_url_id,
            price=model.price,
            currency=model.currency,
            original_price=model.original_price,
            is_available=model.is_available,
            stock_status=model.stock_status,
            stock_quantity=model.stock_quantity,
            source=model.source,
            scraped_at=model.scraped_at,
            created_at=model.created_at,
        )
    
    @staticmethod
    def to_model(entity: PriceHistoryEntity) -> PriceHistoryModel:
        return PriceHistoryModel(
            id=entity.id,
            product_url_id=entity.product_url_id,
            price=entity.price,
            currency=entity.currency,
            original_price=entity.original_price,
            is_available=entity.is_available,
            stock_status=entity.stock_status,
            stock_quantity=entity.stock_quantity,
            source=entity.source,
            scraped_at=entity.scraped_at,
        )


# ============================================================
# Django Repository Implementations
# ============================================================

class DjangoDomainRepository(DomainRepository):
    """Django implementation of DomainRepository.
    
    All operations run in PUBLIC schema.
    """
    
    def _in_public_schema(self):
        """Context manager for public schema operations."""
        return schema_context(get_public_schema_name())
    
    def get_by_id(self, domain_id: UUID) -> Optional[DomainEntity]:
        with self._in_public_schema():
            try:
                model = DomainModel.objects.get(id=domain_id)
                return DomainMapper.to_entity(model)
            except DomainModel.DoesNotExist:
                return None
    
    def get_by_name(self, name: str) -> Optional[DomainEntity]:
        with self._in_public_schema():
            try:
                model = DomainModel.objects.get(name=name.lower())
                return DomainMapper.to_entity(model)
            except DomainModel.DoesNotExist:
                return None
    
    def get_or_create(self, name: str) -> DomainEntity:
        with self._in_public_schema():
            model, created = DomainModel.objects.get_or_create(
                name=name.lower(),
                defaults={
                    'crawl_enabled': True,
                    'is_active': True,
                }
            )
            return DomainMapper.to_entity(model)
    
    def list_active(self) -> List[DomainEntity]:
        with self._in_public_schema():
            models = DomainModel.objects.filter(is_active=True)
            return [DomainMapper.to_entity(m) for m in models]
    
    def update(self, domain: DomainEntity) -> DomainEntity:
        with self._in_public_schema():
            DomainModel.objects.filter(id=domain.id).update(
                crawl_enabled=domain.crawl_enabled,
                crawl_interval_hours=domain.crawl_interval_hours,
                rate_limit_per_minute=domain.rate_limit_per_minute,
                parser_class=domain.parser_class,
                parser_config=domain.parser_config,
                is_active=domain.is_active,
                health_status=domain.health_status,
            )
            return self.get_by_id(domain.id)


class DjangoProductURLRepository(ProductURLRepository):
    """Django implementation of ProductURLRepository.
    
    All operations run in PUBLIC schema.
    """
    
    def _in_public_schema(self):
        """Context manager for public schema operations."""
        return schema_context(get_public_schema_name())
    
    def get_by_id(self, url_id: UUID) -> Optional[ProductURLEntity]:
        with self._in_public_schema():
            try:
                model = ProductURLModel.objects.get(id=url_id)
                return ProductURLMapper.to_entity(model)
            except ProductURLModel.DoesNotExist:
                return None
    
    def get_by_hash(self, url_hash: str) -> Optional[ProductURLEntity]:
        with self._in_public_schema():
            try:
                model = ProductURLModel.objects.get(url_hash=url_hash)
                return ProductURLMapper.to_entity(model)
            except ProductURLModel.DoesNotExist:
                return None
    
    def create(self, product_url: ProductURLEntity) -> ProductURLEntity:
        with self._in_public_schema():
            model = ProductURLMapper.to_model(product_url)
            model.save()
            return ProductURLMapper.to_entity(model)
    
    def increment_reference(self, url_hash: str) -> bool:
        with self._in_public_schema():
            updated = ProductURLModel.objects.filter(url_hash=url_hash).update(
                reference_count=models.F('reference_count') + 1
            )
            return updated > 0
    
    def decrement_reference(self, url_hash: str) -> int:
        with self._in_public_schema():
            with transaction.atomic():
                try:
                    model = ProductURLModel.objects.select_for_update().get(url_hash=url_hash)
                    if model.reference_count > 0:
                        model.reference_count -= 1
                        model.save(update_fields=['reference_count', 'updated_at'])
                    return model.reference_count
                except ProductURLModel.DoesNotExist:
                    return -1
    
    def delete_if_orphaned(self, url_hash: str) -> bool:
        with self._in_public_schema():
            with transaction.atomic():
                deleted, _ = ProductURLModel.objects.filter(
                    url_hash=url_hash,
                    reference_count__lte=0
                ).delete()
                return deleted > 0
    
    def list_for_crawling(self, limit: int = 100) -> List[ProductURLEntity]:
        with self._in_public_schema():
            # Get URLs that:
            # - Are active
            # - Have at least one reference
            # - Haven't been crawled recently
            models = ProductURLModel.objects.filter(
                is_active=True,
                reference_count__gt=0,
            ).select_related('domain').filter(
                domain__crawl_enabled=True
            ).order_by('last_crawled_at')[:limit]
            
            return [ProductURLMapper.to_entity(m) for m in models]
    
    def update_crawl_status(
        self,
        url_hash: str,
        success: bool,
        error: str = ""
    ) -> bool:
        with self._in_public_schema():
            update_fields = {'crawl_error': error if not success else ''}
            if success:
                update_fields['last_crawled_at'] = datetime.utcnow()
            
            updated = ProductURLModel.objects.filter(url_hash=url_hash).update(**update_fields)
            return updated > 0


class DjangoPriceHistoryRepository(PriceHistoryRepository):
    """Django implementation of PriceHistoryRepository.
    
    All operations run in PUBLIC schema.
    """
    
    def _in_public_schema(self):
        """Context manager for public schema operations."""
        return schema_context(get_public_schema_name())
    
    def create(self, price_history: PriceHistoryEntity) -> PriceHistoryEntity:
        with self._in_public_schema():
            model = PriceHistoryMapper.to_model(price_history)
            model.save()
            return PriceHistoryMapper.to_entity(model)
    
    def get_latest_by_url(self, product_url_id: UUID) -> Optional[PriceHistoryEntity]:
        with self._in_public_schema():
            try:
                model = PriceHistoryModel.objects.filter(
                    product_url_id=product_url_id
                ).order_by('-scraped_at').first()
                
                if model:
                    return PriceHistoryMapper.to_entity(model)
                return None
            except PriceHistoryModel.DoesNotExist:
                return None
    
    def get_latest_by_hash(self, url_hash: str) -> Optional[PriceHistoryEntity]:
        with self._in_public_schema():
            try:
                model = PriceHistoryModel.objects.filter(
                    product_url__url_hash=url_hash
                ).order_by('-scraped_at').first()
                
                if model:
                    return PriceHistoryMapper.to_entity(model)
                return None
            except PriceHistoryModel.DoesNotExist:
                return None
    
    def list_by_url(
        self,
        product_url_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PriceHistoryEntity]:
        with self._in_public_schema():
            queryset = PriceHistoryModel.objects.filter(product_url_id=product_url_id)
            
            if start_date:
                queryset = queryset.filter(scraped_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(scraped_at__lte=end_date)
            
            models = queryset.order_by('-scraped_at')[:limit]
            return [PriceHistoryMapper.to_entity(m) for m in models]
    
    def list_by_hash(
        self,
        url_hash: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[PriceHistoryEntity]:
        with self._in_public_schema():
            queryset = PriceHistoryModel.objects.filter(product_url__url_hash=url_hash)
            
            if start_date:
                queryset = queryset.filter(scraped_at__gte=start_date)
            if end_date:
                queryset = queryset.filter(scraped_at__lte=end_date)
            
            models = queryset.order_by('-scraped_at')[:limit]
            return [PriceHistoryMapper.to_entity(m) for m in models]
    
    def get_price_trend(
        self,
        url_hash: str,
        days: int = 30
    ) -> List[PriceHistoryEntity]:
        with self._in_public_schema():
            start_date = datetime.utcnow() - timedelta(days=days)
            
            models = PriceHistoryModel.objects.filter(
                product_url__url_hash=url_hash,
                scraped_at__gte=start_date
            ).order_by('scraped_at')
            
            return [PriceHistoryMapper.to_entity(m) for m in models]
    
    def delete_by_url(self, product_url_id: UUID) -> int:
        with self._in_public_schema():
            deleted, _ = PriceHistoryModel.objects.filter(
                product_url_id=product_url_id
            ).delete()
            return deleted


# Add missing import at the top
from django.db import models as db_models
