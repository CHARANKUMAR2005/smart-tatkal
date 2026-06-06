from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0005_deliverydetails_couriertracking_adminavailability'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='SlotBooking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time_slot', models.CharField(
                    max_length=5,
                    choices=[
                        ('09:00', '9:00 AM – 10:00 AM'),
                        ('10:00', '10:00 AM – 11:00 AM'),
                        ('11:00', '11:00 AM – 12:00 PM'),
                        ('12:00', '12:00 PM – 1:00 PM'),
                        ('14:00', '2:00 PM – 3:00 PM'),
                        ('15:00', '3:00 PM – 4:00 PM'),
                        ('16:00', '4:00 PM – 5:00 PM'),
                    ],
                )),
                ('token_number', models.CharField(max_length=10)),
                ('status', models.CharField(
                    max_length=20,
                    choices=[
                        ('booked', 'Booked'),
                        ('completed', 'Completed'),
                        ('cancelled', 'Cancelled'),
                        ('no_show', 'No Show'),
                    ],
                    default='booked',
                )),
                ('booked_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True)),
                ('user', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='slot_bookings',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('application', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='slot_bookings',
                    to='certificates.application',
                )),
            ],
            options={
                'ordering': ['date', 'time_slot', 'booked_at'],
            },
        ),
    ]
