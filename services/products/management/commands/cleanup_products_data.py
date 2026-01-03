import sys
from typing import List
from django.core.management.base import BaseCommand
from django.db import connection
from django_tenants.utils import get_public_schema_name, schema_context

try:
    from core.tenants.infrastructure.django_models import Tenant
except Exception:
    Tenant = None  # Fallback if tenants model not available

# Tables in public schema (order matters for FK cleanup)
PUBLIC_TABLES = [
    "products_price_history",
    "products_shared_url",
    "products_shared_product",
]

# Tables in each tenant schema (order matters for FK cleanup)
TENANT_TABLES = [
    "products_tenant_url_tracking",
    "products_tenant_product",
]


class Command(BaseCommand):
    help = "Cleanup all products data across public and tenant schemas (destructive)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--confirm",
            action="store_true",
            help="Actually execute the cleanup. Without this flag it will dry-run.",
        )
        parser.add_argument(
            "--schemas",
            nargs="*",
            default=[],
            help="Optional list of tenant schema names to clean. If empty, clean all tenants.",
        )

    def handle(self, *args, **options):
        if Tenant is None:
            self.stderr.write("Tenant model not found; aborting cleanup.")
            sys.exit(1)

        confirm = options["confirm"]
        target_schemas: List[str] = options["schemas"]

        # Collect schemas
        public_schema = get_public_schema_name()
        tenant_qs = Tenant.objects.all()
        if target_schemas:
            tenant_qs = tenant_qs.filter(schema_name__in=target_schemas)
        tenant_schemas = list(tenant_qs.values_list("schema_name", flat=True))

        self.stdout.write("Cleanup plan:")
        self.stdout.write(f"  Public schema: {public_schema}")
        self.stdout.write(f"  Tenant schemas: {tenant_schemas if tenant_schemas else '[]'}")
        self.stdout.write(f"  Mode: {'EXECUTE' if confirm else 'DRY-RUN'}")

        # Dry-run only shows plan
        if not confirm:
            self.stdout.write("Dry-run complete. Re-run with --confirm to execute.")
            return

        # Cleanup public schema tables
        with schema_context(public_schema):
            with connection.cursor() as cursor:
                for table in PUBLIC_TABLES:
                    cursor.execute(f"TRUNCATE TABLE \"{table}\" CASCADE;")
                    self.stdout.write(f"[public] truncated {table}")

        # Cleanup tenant schemas tables
        for schema in tenant_schemas:
            with schema_context(schema):
                with connection.cursor() as cursor:
                    for table in TENANT_TABLES:
                        cursor.execute(f"TRUNCATE TABLE \"{table}\" CASCADE;")
                        self.stdout.write(f"[{schema}] truncated {table}")

        self.stdout.write(self.style.SUCCESS("Products data cleanup completed."))
