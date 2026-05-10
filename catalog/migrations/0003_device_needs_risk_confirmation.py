from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0002_botcontent"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="needs_risk_confirmation",
            field=models.BooleanField(default=False, verbose_name="Согласовывайте риски с клиентом"),
        ),
    ]
