from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('payments', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='payment',
            name='payment_screenshot',
            field=models.ImageField(blank=True, null=True, upload_to='payment_screenshots/'),
        ),
    ]
