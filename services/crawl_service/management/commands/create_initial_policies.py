"""
Management command to create initial CrawlPolicy for all existing domains.

Usage:
    python manage.py create_initial_policies
    
This creates 1 default policy per domain with standard crawl frequency.
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from services.products_shared.infrastructure.django_models import Domain
from services.crawl_service.models import CrawlPolicy


class Command(BaseCommand):
    help = 'Create initial CrawlPolicy for all domains in products_shared'

    def add_arguments(self, parser):
        parser.add_argument(
            '--frequency',
            type=int,
            default=24,
            help='Default frequency hours (default: 24)'
        )
        parser.add_argument(
            '--priority',
            type=int,
            default=5,
            choices=[1, 5, 10, 20],
            help='Default priority (1=Low, 5=Normal, 10=High, 20=Urgent)'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        frequency = options['frequency']
        priority = options['priority']
        
        domains = Domain.objects.all()
        
        if not domains.exists():
            self.stdout.write(self.style.WARNING('No domains found in products_shared'))
            return
        
        created_count = 0
        skipped_count = 0
        
        for domain in domains:
            # Check if policy already exists
            if CrawlPolicy.objects.filter(domain=domain).exists():
                self.stdout.write(f'Skipped {domain.name} - policy already exists')
                skipped_count += 1
                continue
            
            # Create default policy
            policy = CrawlPolicy.objects.create(
                domain=domain,
                name='Default Policy',
                url_pattern='',  # Empty = match all URLs
                frequency_hours=frequency,
                priority=priority,
                max_retries=3,
                retry_backoff_minutes=5,
                timeout_minutes=10,
                enabled=True,
                next_run_at=timezone.now()
            )
            
            self.stdout.write(self.style.SUCCESS(
                f'✓ Created policy for {domain.name} (priority={priority}, freq={frequency}h)'
            ))
            created_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'\nSummary: Created {created_count} policies, skipped {skipped_count}'
        ))
