import logging
from django.core.management.base import BaseCommand

from services.crawl_service.utils import create_jobs_from_shared

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Import CrawlJob entries from services.products_shared ProductURL table'

    def add_arguments(self, parser):
        parser.add_argument('--rule', required=True, help='ScheduleRule UUID to assign to jobs')
        parser.add_argument('--domain', help='Filter by domain name (e.g., amazon.co.jp)')
        parser.add_argument('--limit', type=int, help='Maximum number of URLs to import')
        parser.add_argument('--only-active', action='store_true', default=False, help='Import only active ProductURL entries')
        parser.add_argument('--use-raw-url', action='store_true', default=False, help='Use raw_url instead of normalized_url')
        parser.add_argument('--dry-run', action='store_true', default=False, help='Show count without creating jobs')

    def handle(self, *args, **options):
        rule_id = options['rule']
        domain = options.get('domain')
        limit = options.get('limit')
        only_active = options.get('only_active')
        use_normalized = not options.get('use_raw_url')
        dry_run = options.get('dry_run')

        if dry_run:
            self.stdout.write(self.style.WARNING('Dry-run mode: will not create jobs'))

        try:
            if dry_run:
                # Count prospective URLs
                from services.products_shared.infrastructure.django_models import ProductURL, Domain
                qs = ProductURL.objects.all()
                if only_active:
                    qs = qs.filter(is_active=True)
                if domain:
                    try:
                        d = Domain.objects.get(name=domain)
                        qs = qs.filter(domain=d)
                    except Domain.DoesNotExist:
                        self.stdout.write(self.style.ERROR(f'Domain not found: {domain}'))
                        return
                if limit:
                    qs = qs[:int(limit)]
                count = qs.count()
                self.stdout.write(self.style.SUCCESS(f'Would import {count} jobs (dry-run)'))
                return

            created = create_jobs_from_shared(
                schedule_rule_id=rule_id,
                domain_name=domain,
                limit=limit,
                only_active=only_active,
                use_normalized_url=use_normalized,
            )
            self.stdout.write(self.style.SUCCESS(f'Imported {created} jobs'))
        except Exception as e:
            logger.exception('Error importing jobs from shared products')
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            raise
