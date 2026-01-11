"""Ensure the base JobResetRule exists and update its configuration."""

from django.core.management.base import BaseCommand
from django.utils import timezone

from services.crawl_service.models import JobResetRule


class Command(BaseCommand):
    help = 'Create or update the global base JobResetRule (selection_type=all)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--name',
            type=str,
            default='Base Policy',
            help='Display name for the base policy'
        )
        parser.add_argument(
            '--frequency',
            type=int,
            default=24,
            help='Default frequency hours (default: 24)'
        )
        # Legacy args removed; JobResetRule only needs name + frequency

    def handle(self, *args, **options):
        # Ensure a global ALL selection JobResetRule exists
        rule = JobResetRule.objects.filter(selection_type=JobResetRule.SelectionType.ALL).first()

        if rule:
            rule.name = options['name']
            rule.frequency_hours = options['frequency']
            rule.rule_tag = rule.rule_tag or 'base'
            rule.enabled = True
            rule.save()
            self.stdout.write(self.style.SUCCESS('✓ Base JobResetRule updated'))
            return

        rule = JobResetRule.objects.create(
            name=options['name'],
            selection_type=JobResetRule.SelectionType.ALL,
            rule_tag='base',
            frequency_hours=options['frequency'],
            enabled=True,
        )

        self.stdout.write(self.style.SUCCESS(f'✓ Base JobResetRule created ({rule.name})'))
