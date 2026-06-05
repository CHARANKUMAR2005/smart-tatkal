import csv
import os
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from accounts.models import College

HEADER_ALIASES = {
    'college_code': ['college_code', 'code', 'collegeid', 'institution_code'],
    'college_name': ['college_name', 'name', 'institution_name', 'college_name'],
    'university_name': ['university_name', 'university', 'university_affiliation', 'affiliation'],
    'state': ['state', 'province', 'region'],
    'district': ['district', 'city', 'town', 'district_name'],
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
    header_terms.update({'ownership', 'name'})
    values = [normalize_value(v) for v in record.values() if v is not None]
    if not values:
        return False
    header_like = sum(1 for value in values if value in header_terms)
    return header_like >= max(2, len(values) // 2)


def make_code(name, existing_codes):
    base = slugify(name).replace('-', '_')
    if not base:
        base = 'college'
    candidate = base
    index = 1
    while candidate in existing_codes:
        index += 1
        candidate = f'{base}_{index}'
    return candidate


def normalize_row_headers(row):
    return {str(key).strip().lower(): value for key, value in row.items() if key is not None}


def find_existing_college(code, name, university_name, state, district):
    if code:
        existing = College.objects.filter(college_code__iexact=code).first()
        if existing:
            return existing
    if not name:
        return None
    qs = College.objects.filter(college_name__iexact=name)
    if university_name:
        qs = qs.filter(university_name__iexact=university_name)
    if state:
        qs = qs.filter(state__iexact=state)
    if district:
        qs = qs.filter(district__iexact=district)
    return qs.first()


def load_csv(path):
    with open(path, newline='', encoding='utf-8') as csvfile:
        reader = csv.reader(csvfile)
        rows = [row for row in reader if row and any(str(cell).strip() for cell in row)]

    if not rows:
        return []

    header_row = [str(cell).strip().lower() for cell in rows[0]]
    aliases = HEADER_ALIASES['college_name'] + HEADER_ALIASES['college_code'] + HEADER_ALIASES['university_name'] + HEADER_ALIASES['state'] + HEADER_ALIASES['district'] + HEADER_ALIASES['is_active']
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


def load_excel(path):
    try:
        import openpyxl
    except ImportError as exc:
        raise CommandError('openpyxl is required to import Excel files. Install it with pip install openpyxl.') from exc

    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    worksheet = workbook.active
    rows = list(worksheet.iter_rows(values_only=True))
    if not rows:
        return []

    headers = [str(cell).strip().lower() if cell is not None else '' for cell in rows[0]]
    data = []
    for row in rows[1:]:
        if not any(cell is not None for cell in row):
            continue
        record = {headers[i]: row[i] for i in range(min(len(headers), len(row))) if headers[i]}
        data.append(record)
    return data


class Command(BaseCommand):
    help = 'Import colleges from a CSV or Excel file into the College table.'

    def add_arguments(self, parser):
        parser.add_argument('file_path', type=str, help='Path to the colleges CSV or Excel file.')
        parser.add_argument('--truncate', action='store_true', help='Delete existing College records before loading.')

    def handle(self, *args, **options):
        file_path = options['file_path']
        truncate = options['truncate']

        if not os.path.exists(file_path):
            raise CommandError(f'File not found: {file_path}')

        if truncate:
            College.objects.all().delete()
            self.stdout.write(self.style.WARNING('Deleted existing college records.'))

        ext = os.path.splitext(file_path)[1].lower()
        if ext == '.csv':
            rows = load_csv(file_path)
        elif ext in ('.xls', '.xlsx'):
            rows = load_excel(file_path)
        else:
            raise CommandError('Unsupported file format. Use CSV, XLS, or XLSX.')

        existing_codes = set(College.objects.values_list('college_code', flat=True))
        created = 0
        updated = 0
        skipped = 0

        for row in rows:
            if isinstance(row, dict):
                if is_header_row(row):
                    continue
                college_name = get_column(row, HEADER_ALIASES['college_name'])
                college_code = get_column(row, HEADER_ALIASES['college_code'])
                university_name = get_column(row, HEADER_ALIASES['university_name'])
                state = get_column(row, HEADER_ALIASES['state'])
                district = get_column(row, HEADER_ALIASES['district'])
                is_active = str_to_bool(get_column(row, HEADER_ALIASES['is_active'], 'true'))
            else:
                college_name = str(row[0]).strip() if len(row) > 0 else ''
                college_code = None
                university_name = ''
                state = str(row[2]).strip() if len(row) > 2 else ''
                district = str(row[3]).strip() if len(row) > 3 else ''
                is_active = True

            if not college_name:
                skipped += 1
                continue

            existing = find_existing_college(college_code, college_name, university_name, state, district)
            if existing:
                college_code = existing.college_code
            elif not college_code:
                college_code = make_code(college_name, existing_codes)

            existing_codes.add(college_code)

            defaults = {
                'college_name': college_name,
                'university_name': university_name,
                'state': state,
                'district': district,
                'is_active': is_active,
            }

            college, created_flag = College.objects.update_or_create(
                college_code=college_code,
                defaults=defaults
            )
            if created_flag:
                created += 1
            else:
                updated += 1

        self.stdout.write(self.style.SUCCESS(
            f'Colleges processed: {created + updated}, created: {created}, updated: {updated}, skipped: {skipped}.'
        ))
