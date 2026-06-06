from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0004_add_college_to_application'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='DeliveryDetails',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('method', models.CharField(choices=[('collect', 'Collect from College'), ('home', 'Home Delivery')], default='collect', max_length=10)),
                ('house_no', models.CharField(blank=True, max_length=50)),
                ('street', models.CharField(blank=True, max_length=200)),
                ('area', models.CharField(blank=True, max_length=200)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('state', models.CharField(blank=True, max_length=100)),
                ('pincode', models.CharField(blank=True, max_length=10)),
                ('mobile', models.CharField(blank=True, max_length=15)),
                ('delivery_fee', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery', to='certificates.application')),
            ],
        ),
        migrations.CreateModel(
            name='CourierTracking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('courier_name', models.CharField(blank=True, max_length=100)),
                ('tracking_number', models.CharField(blank=True, db_index=True, max_length=100)),
                ('dispatch_date', models.DateField(blank=True, null=True)),
                ('expected_delivery_date', models.DateField(blank=True, null=True)),
                ('tracking_status', models.CharField(choices=[('printed', 'Printed'), ('dispatched', 'Dispatched'), ('in_transit', 'In Transit'), ('delivered', 'Delivered')], default='printed', max_length=20)),
                ('notes', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('application', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='tracking', to='certificates.application')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='AdminAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(unique=True)),
                ('status', models.CharField(choices=[('available', 'Available'), ('busy', 'Busy'), ('holiday', 'Holiday'), ('half_day', 'Half Day')], default='available', max_length=20)),
                ('notes', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('set_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name_plural': 'Admin Availabilities',
                'ordering': ['date'],
            },
        ),
    ]
