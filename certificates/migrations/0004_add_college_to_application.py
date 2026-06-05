from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):

    dependencies = [
        ('certificates', '0003_remove_application_university_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='application',
            name='college',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='applications', to='accounts.college'),
        ),
    ]
