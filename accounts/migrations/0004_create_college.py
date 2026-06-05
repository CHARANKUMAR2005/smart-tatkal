from django.db import migrations, models
import django.db.models.deletion
import django.db.models.functions

class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_institution_remove_studentprofile_university_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='College',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('college_code', models.CharField(max_length=50, unique=True)),
                ('college_name', models.CharField(db_index=True, max_length=255)),
                ('university_name', models.CharField(blank=True, max_length=255)),
                ('state', models.CharField(blank=True, db_index=True, max_length=100)),
                ('district', models.CharField(blank=True, max_length=100)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['college_name'],
                'indexes': [
                    models.Index(django.db.models.functions.Lower('college_name'), name='college_name_lower_idx'),
                    models.Index(django.db.models.functions.Lower('college_code'), name='college_code_lower_idx'),
                    models.Index(django.db.models.functions.Lower('university_name'), name='university_name_lower_idx'),
                ],
            },
        ),
    ]
