from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import connection, transaction, models


class Command(BaseCommand):
    help = "Scan all models with DecimalField values and optionally fix corrupted values."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List invalid rows without changing any data.',
        )
        parser.add_argument(
            '--auto-fix',
            action='store_true',
            help='Automatically fix invalid DecimalField values to 0.00.',
        )
        parser.add_argument(
            '--auto-delete',
            action='store_true',
            help='Automatically delete rows with invalid DecimalField values.',
        )

    def handle(self, *args, dry_run=False, auto_fix=False, auto_delete=False, **options):
        if auto_fix and auto_delete:
            self.stdout.write(self.style.ERROR('Use either --auto-fix or --auto-delete, not both.'))
            return

        user_model = get_user_model()
        decimal_models = self.find_decimal_models()

        if not decimal_models:
            self.stdout.write(self.style.SUCCESS('No models with DecimalField values were found.'))
            return

        self.stdout.write(self.style.NOTICE('Models with DecimalField values:'))
        for model, fields in decimal_models:
            field_names = ', '.join(field.name for field in fields)
            self.stdout.write(f'- {model._meta.label}: {field_names}')
            relation_fields = self.get_relation_fields(model)
            if relation_fields:
                for field_name, relation_type, related_model_label in relation_fields:
                    self.stdout.write(f'    {field_name}: {relation_type} -> {related_model_label}')
            else:
                self.stdout.write('    No direct ForeignKey/OneToOne relations.')

            user_paths = self.find_user_paths(model, user_model)
            if user_paths:
                for path in user_paths:
                    self.stdout.write(f'    User path: {" -> ".join(path)}')
            else:
                self.stdout.write('    No User path found.')

        self.stdout.write('')

        for model, fields in decimal_models:
            self.scan_model(model, fields, dry_run, auto_fix, auto_delete)

    def find_decimal_models(self):
        candidate_models = []
        for model in apps.get_models():
            decimal_fields = [field for field in model._meta.fields if isinstance(field, models.DecimalField)]
            if decimal_fields:
                candidate_models.append((model, decimal_fields))
        return candidate_models

    def get_relation_fields(self, model):
        relation_fields = []
        for field in model._meta.fields:
            if not getattr(field, 'is_relation', False):
                continue
            if not (field.many_to_one or field.one_to_one):
                continue
            related_model_label = self.get_related_model_label(field)
            relation_type = 'OneToOneField' if field.one_to_one else 'ForeignKey'
            relation_fields.append((field.name, relation_type, related_model_label))
        return relation_fields

    def get_related_model_label(self, field):
        related_model = field.remote_field.model
        try:
            return related_model._meta.label
        except Exception:
            return str(related_model)

    def find_user_paths(self, model, user_model, visited=None, path=None, depth=0):
        if path is None:
            path = [model._meta.label]
        if model == user_model:
            return [path]
        if depth >= 6:
            return []

        visited = visited or set()
        visited.add(model)
        paths = []

        for field in model._meta.fields:
            if not getattr(field, 'is_relation', False):
                continue
            if not (field.many_to_one or field.one_to_one):
                continue
            related_model = field.remote_field.model
            if related_model in visited:
                continue
            child_paths = self.find_user_paths(
                related_model,
                user_model,
                visited=visited.copy(),
                path=path + [related_model._meta.label],
                depth=depth + 1,
            )
            paths.extend(child_paths)

        return paths

    def scan_model(self, model, decimal_fields, dry_run, auto_fix, auto_delete):
        table_name = model._meta.db_table
        pk_field = model._meta.pk
        pk_column = pk_field.column
        field_columns = [(field.name, field.column) for field in decimal_fields]

        self.stdout.write(self.style.MIGRATE_HEADING(f'Scanning {model._meta.label} ({table_name})'))

        with connection.cursor() as cursor:
            columns = ', '.join(f'"{column}"' for _, column in field_columns)
            cursor.execute(f'SELECT "{pk_column}", {columns} FROM "{table_name}"')
            rows = cursor.fetchall()

        bad_rows = []
        for row in rows:
            pk_value = row[0]
            for (field_name, column), raw_value in zip(field_columns, row[1:]):
                if self.is_invalid_decimal(raw_value):
                    bad_rows.append((pk_value, field_name, column, raw_value))

        if not bad_rows:
            self.stdout.write(self.style.SUCCESS('  No invalid values found.'))
            self.stdout.write('')
            return

        self.stdout.write(self.style.WARNING(f'  Found {len(bad_rows)} invalid DecimalField values.'))

        for pk_value, field_name, column, raw_value in bad_rows:
            self.stdout.write('')
            self.stdout.write(f'  Model: {model._meta.label}')
            self.stdout.write(f'  PK: {pk_value}')
            self.stdout.write(f'  Field: {field_name} ({column})')
            self.stdout.write(f'  Bad value: {repr(raw_value)}')

            if dry_run:
                self.stdout.write(self.style.NOTICE('  Dry run enabled, skipping changes.'))
                continue

            if auto_fix:
                self.update_field(table_name, column, pk_column, pk_value)
                continue
            if auto_delete:
                self.delete_row(table_name, pk_column, pk_value)
                continue

            action = self.prompt_action()
            if action == 'f':
                self.update_field(table_name, column, pk_column, pk_value)
            elif action == 'd':
                self.delete_row(table_name, pk_column, pk_value)
            elif action == 's':
                self.stdout.write(self.style.NOTICE('  Skipping this row.'))
            elif action == 'q':
                self.stdout.write(self.style.NOTICE('  Aborting further changes.'))
                return

        self.stdout.write('')

    def is_invalid_decimal(self, raw_value):
        if raw_value is None:
            return False
        try:
            Decimal(raw_value)
            return False
        except (InvalidOperation, TypeError, ValueError):
            return True

    def prompt_action(self):
        prompt = '  Choose [f]ix to 0.00, [d]elete row, [s]kip, [q]uit: '
        while True:
            choice = input(prompt).strip().lower()
            if choice in {'f', 'd', 's', 'q'}:
                return choice
            self.stdout.write('  Enter f, d, s, or q.')

    @transaction.atomic
    def update_field(self, table_name, column, pk_column, pk_value):
        with connection.cursor() as cursor:
            cursor.execute(
                f'UPDATE "{table_name}" SET "{column}" = ? WHERE "{pk_column}" = ?',
                [Decimal('0.00'), pk_value],
            )
        self.stdout.write(self.style.SUCCESS('  Updated to 0.00.'))

    @transaction.atomic
    def delete_row(self, table_name, pk_column, pk_value):
        with connection.cursor() as cursor:
            cursor.execute(
                f'DELETE FROM "{table_name}" WHERE "{pk_column}" = ?',
                [pk_value],
            )
        self.stdout.write(self.style.SUCCESS('  Deleted row.'))
