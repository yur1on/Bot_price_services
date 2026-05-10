from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Device",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("brand", models.CharField(blank=True, max_length=120, verbose_name="Бренд")),
                ("model_name", models.CharField(max_length=255, unique=True, verbose_name="Модель")),
                ("normalized_name", models.CharField(db_index=True, max_length=255, verbose_name="Нормализованное имя")),
                ("glass_replacement_price", models.DecimalField(decimal_places=2, max_digits=8, verbose_name="Только переклейка стекла")),
                (
                    "glass_replacement_without_disassembly_price",
                    models.DecimalField(decimal_places=2, max_digits=8, verbose_name="Выклейка и переклейка"),
                ),
                (
                    "turnkey_price",
                    models.DecimalField(
                        blank=True,
                        decimal_places=2,
                        help_text="Оставьте пустым, если цена договорная.",
                        max_digits=8,
                        null=True,
                        verbose_name="Переклейка под ключ",
                    ),
                ),
                ("is_active", models.BooleanField(default=True, verbose_name="Активно")),
            ],
            options={
                "verbose_name": "Устройство",
                "verbose_name_plural": "Устройства",
                "ordering": ["brand", "model_name"],
            },
        ),
        migrations.CreateModel(
            name="TelegramUser",
            fields=[
                ("telegram_id", models.BigIntegerField(primary_key=True, serialize=False, verbose_name="Telegram ID")),
                ("name", models.CharField(blank=True, max_length=255, verbose_name="Имя")),
                ("workshop_address", models.CharField(blank=True, max_length=255, verbose_name="Мастерская / адрес")),
                ("is_blocked", models.BooleanField(default=False, verbose_name="Заблокирован")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Создан")),
                ("updated_at", models.DateTimeField(auto_now=True, verbose_name="Обновлен")),
            ],
            options={
                "verbose_name": "Пользователь Telegram",
                "verbose_name_plural": "Пользователи Telegram",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="QueryLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telegram_id", models.BigIntegerField(db_index=True, verbose_name="Telegram ID")),
                ("query", models.CharField(max_length=255, verbose_name="Запрос")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Дата")),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="queries",
                        to="catalog.telegramuser",
                        verbose_name="Пользователь",
                    ),
                ),
            ],
            options={
                "verbose_name": "Запрос пользователя",
                "verbose_name_plural": "Запросы пользователей",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="DisplayOption",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "display_type",
                    models.CharField(
                        choices=[("original", "Оригинал"), ("copy", "Копия")],
                        max_length=20,
                        verbose_name="Тип дисплея",
                    ),
                ),
                ("price", models.DecimalField(decimal_places=2, default=0, max_digits=8, verbose_name="Стоимость")),
                ("stock", models.PositiveIntegerField(default=0, verbose_name="Остаток")),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="display_options",
                        to="catalog.device",
                        verbose_name="Устройство",
                    ),
                ),
            ],
            options={
                "verbose_name": "Дисплей",
                "verbose_name_plural": "Дисплеи",
                "ordering": ["device__model_name", "display_type"],
                "unique_together": {("device", "display_type")},
            },
        ),
    ]
