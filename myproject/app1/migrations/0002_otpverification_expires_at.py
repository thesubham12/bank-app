from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app1', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='otpverification',
            name='expires_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
