import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0003_device_needs_risk_confirmation"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="success_rate",
            field=models.PositiveSmallIntegerField(
                blank=True,
                help_text="Укажите вероятность успеха в процентах, например 90 или 50.",
                null=True,
                validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)],
                verbose_name="Процент успеха",
            ),
        ),
    ]
