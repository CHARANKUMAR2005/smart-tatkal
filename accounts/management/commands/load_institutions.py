import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from accounts.models import Institution


HEADER_ALIASES = {
    'code': ['code', 'institution_code', 'college_code', 'collegeid', 'id'],
    'name': ['name', 'institution_name', 'college_name', 'inst_name'],
    'institution_type': ['institution_type', 'type', 'category', 'institution_category'],
    'city': ['city', 'town', 'district'],
    'state': ['state', 'province', 'region'],
    'is_active': ['is_active', 'active', 'status'],
}


def get_column(row, aliases, default=''):
    for key in aliases:
        if key in row and row[key] is not None:
            value = str(row[key]).strip()
            if value:
                return value
    return default


def str_to_bool(value):
    if isinstance(value, bool):
        return value
    value = str(value).strip().lower()
    return value in ('1', 'true', 'yes', 'y', 'active', 'published')


def normalize_value(value):
    return str(value).strip().lower()


def is_header_row(record):
    header_terms = {alias.lower() for aliases in HEADER_ALIASES.values() for alias in aliases}
    header_terms.update({'ownership', 'district'})
    values = [normalize_value(v) for v in record.values() if v is not None]
    if not values:
        return False
    header_like = sum(1 for value in values if value in header_terms)
    return header_like >= max(2, len(values) // 2)


def make_code(name, existing_codes):
    base = slugify(name).replace('-', '_')
    if not base:
        base = 'institution'
    candidate = base
    index = 1
    while candidate in existing_codes:
        index += 1
        candidate = f'{base}_{index}'
    return candidate


def normalize_row_headers(row):
    return {str(key).strip().lower(): value for key, value in row.items() if key is not None}


def find_existing_institution(code, name, city, state):
    if code:
        existing = Institution.objects.filter(code__iexact=code).first()
        if existing:
            return existing
    if not name:
        return None
    qs = Institution.objects.filter(name__iexact=name)
    if city:
        qs = qs.filter(city__iexact=city)
    if state:
        qs = qs.filter(state__iexact=state)
    return qs.first()


def load_csv(path):
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows = [row for row in reader if row and any(str(cell).strip() for cell in row)]

    if not rows:
        return []

    header_row = [str(cell).strip().lower() for cell in rows[0]]
    aliases = HEADER_ALIASES['name'] + HEADER_ALIASES['code'] + HEADER_ALIASES['institution_type'] + HEADER_ALIASES['city'] + HEADER_ALIASES['state'] + HEADER_ALIASES['is_active']
    if any(alias in header_row for alias in aliases):
        records = []
        for row in rows[1:]:
            if not any(str(cell).strip() for cell in row):
                continue
            record = {header_row[i]: row[i] for i in range(min(len(header_row), len(row))) if header_row[i]}
            records.append(normalize_row_headers(record))
        return records

    # Treat as headerless CSV: positional columns
    return rows


class Command(BaseCommand):
    help = 'Load institutions from a CSV file into the Institution table.'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str, help='Path to the institutions CSV file.')
        parser.add_argument('--truncate', action='store_true', help='Delete existing Institution records before loading.')

    def handle(self, *args, **options):
        csv_path = options['csv_path']
        truncate = options['truncate']

        if truncate:
            Institution.objects.all().delete()
            self.stdout.write(self.style.WARNING('Deleted existing institutions.'))

        existing_codes = set(Institution.objects.values_list('code', flat=True))
        created = 0
        updated = 0

        ext = os.path.splitext(csv_path)[1].lower()
        if ext == '.csv':
            rows = load_csv(csv_path)
        else:
            raise CommandError('Unsupported file format. Use CSV, XLS, or XLSX.')

        for row in rows:
            if isinstance(row, dict):
                if is_header_row(row):
                    continue
                name = get_column(row, HEADER_ALIASES['name'])
                code = get_column(row, HEADER_ALIASES['code'])
                institution_type = get_column(row, HEADER_ALIASES['institution_type'], 'college') or 'college'
                city = get_column(row, HEADER_ALIASES['city'])
                state = get_column(row, HEADER_ALIASES['state'])
                is_active = str_to_bool(get_column(row, HEADER_ALIASES['is_active'], 'true'))
            else:
                name = str(row[0]).strip() if len(row) > 0 else ''
                code = None
                institution_type = str(row[1]).strip() if len(row) > 1 else 'college'
                city = str(row[2]).strip() if len(row) > 2 else ''
                state = str(row[3]).strip() if len(row) > 3 else ''
                is_active = True

            if not name:
                continue

            existing = find_existing_institution(code, name, city, state)
            if existing:
                code = existing.code
            elif not code:
                code = make_code(name, existing_codes)

            existing_codes.add(code)

            defaults = {
                'name': name,
                'institution_type': institution_type,
                'city': city,
                'state': state,
                'is_active': is_active,
            }
            institution, created_flag = Institution.objects.update_or_create(code=code, defaults=defaults)
            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Institutions loaded: {created} created, {updated} updated.'
        ))
