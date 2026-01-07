"""
Management command to manually submit results for locked jobs.

Usage:
    python manage.py submit_locked_jobs --all
    python manage.py submit_locked_jobs --job-id <uuid>
    python manage.py submit_locked_jobs --bot-id <bot-id>
    python manage.py submit_locked_jobs --expired-only
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from decimal import Decimal
import uuid

from services.crawl_service.models import CrawlJob, CrawlResult, CrawlPolicy


class Command(BaseCommand):
    help = 'Manually submit results for locked jobs (for testing/recovery)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Submit all locked jobs with mock data',
        )
        parser.add_argument(
            '--job-id',
            type=str,
            help='Submit specific job by ID',
        )
        parser.add_argument(
            '--bot-id',
            type=str,
            help='Submit all jobs locked by specific bot',
        )
        parser.add_argument(
            '--expired-only',
            action='store_true',
            help='Submit only expired locked jobs',
        )
        parser.add_argument(
            '--price',
            type=float,
            default=99000.0,
            help='Mock price to submit (default: 99000.0)',
        )
        parser.add_argument(
            '--currency',
            type=str,
            default='VND',
            help='Currency code (default: VND)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without actually doing it',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        price = Decimal(str(options['price']))
        currency = options['currency']

        # Build query
        jobs = CrawlJob.objects.filter(status='locked')

        if options['job_id']:
            try:
                job_uuid = uuid.UUID(options['job_id'])
                jobs = jobs.filter(id=job_uuid)
            except ValueError:
                raise CommandError(f"Invalid UUID: {options['job_id']}")

        elif options['bot_id']:
            jobs = jobs.filter(locked_by=options['bot_id'])

        elif options['expired_only']:
            # Filter only expired jobs
            jobs = [job for job in jobs if job.is_lock_expired()]
            self.stdout.write(f"Found {len(jobs)} expired locked jobs")

        elif not options['all']:
            raise CommandError(
                "Must specify one of: --all, --job-id, --bot-id, or --expired-only"
            )

        # Convert to list if needed
        if not isinstance(jobs, list):
            jobs = list(jobs)

        if not jobs:
            self.stdout.write(self.style.WARNING("No locked jobs found"))
            return

        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Found {len(jobs)} locked job(s) to submit")
        self.stdout.write(f"{'='*60}\n")

        success_count = 0
        error_count = 0

        for job in jobs:
            self.stdout.write(f"\nJob: {job.id}")
            self.stdout.write(f"  URL: {job.url[:80]}...")
            self.stdout.write(f"  Locked by: {job.locked_by}")
            self.stdout.write(f"  Locked at: {job.locked_at}")
            self.stdout.write(f"  Expired: {job.is_lock_expired()}")

            if dry_run:
                self.stdout.write(self.style.WARNING("  [DRY RUN] Would submit result"))
                continue

            try:
                # Create result
                result = CrawlResult.objects.create(
                    job=job,
                    price=price,
                    currency=currency,
                    title=f"Manual submission for {job.url[:50]}",
                    in_stock=True,
                    parsed_data={'manual': True, 'submitted_at': str(timezone.now())},
                    raw_html='<html>Manual submission - no HTML captured</html>',
                    crawled_at=timezone.now(),
                )

                # Mark job as done
                job.mark_done()

                # Reschedule policy if exists
                if job.policy:
                    job.policy.schedule_next_run(success=True)
                    self.stdout.write(
                        f"  Policy next run: {job.policy.next_run_at}"
                    )

                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Result created: {result.id}")
                )
                self.stdout.write(
                    self.style.SUCCESS(f"  ✓ Job marked as DONE")
                )
                success_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f"  ✗ Error: {str(e)}")
                )
                error_count += 1

        # Summary
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"SUMMARY:")
        self.stdout.write(f"  Success: {success_count}")
        self.stdout.write(f"  Errors: {error_count}")
        if dry_run:
            self.stdout.write(self.style.WARNING("  (DRY RUN - no changes made)"))
        self.stdout.write(f"{'='*60}\n")
