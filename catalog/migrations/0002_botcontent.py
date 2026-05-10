from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("catalog", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="BotContent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.CharField(max_length=100, unique=True, verbose_name="Код")),
                ("title", models.CharField(max_length=255, verbose_name="Название")),
                ("content", models.TextField(blank=True, verbose_name="Текст")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
            ],
            options={
                "verbose_name": "Текст бота",
                "verbose_name_plural": "Тексты бота",
            },
        ),
    ]
