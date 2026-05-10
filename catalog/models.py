from django.db import models


class Device(models.Model):
    class Meta:
        verbose_name = "Устройство"
        verbose_name_plural = "Устройства"
        ordering = ["brand", "model_name"]

    brand = models.CharField("Бренд", max_length=120, blank=True)
    model_name = models.CharField("Модель", max_length=255, unique=True)
    normalized_name = models.CharField("Нормализованное имя", max_length=255, db_index=True)
    glass_replacement_price = models.DecimalField("Только переклейка стекла", max_digits=8, decimal_places=2)
    glass_replacement_without_disassembly_price = models.DecimalField(
        "Выклейка и переклейка",
        max_digits=8,
        decimal_places=2,
    )
    turnkey_price = models.DecimalField(
        "Переклейка под ключ",
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Оставьте пустым, если цена договорная.",
    )
    is_active = models.BooleanField("Активно", default=True)

    def __str__(self):
        return self.model_name

    def save(self, *args, **kwargs):
        self.normalized_name = normalize_text(self.model_name)
        if not self.brand:
            self.brand = self.model_name.split()[0]
        super().save(*args, **kwargs)


class DisplayOption(models.Model):
    class DisplayType(models.TextChoices):
        ORIGINAL = "original", "Оригинал"
        COPY = "copy", "Копия"

    class Meta:
        verbose_name = "Дисплей"
        verbose_name_plural = "Дисплеи"
        ordering = ["device__model_name", "display_type"]
        unique_together = ("device", "display_type")

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="display_options", verbose_name="Устройство")
    display_type = models.CharField("Тип дисплея", max_length=20, choices=DisplayType.choices)
    price = models.DecimalField("Стоимость", max_digits=8, decimal_places=2, default=0)
    stock = models.PositiveIntegerField("Остаток", default=0)

    def __str__(self):
        return f"{self.device.model_name} ({self.get_display_type_display()})"


class TelegramUser(models.Model):
    class Meta:
        verbose_name = "Пользователь Telegram"
        verbose_name_plural = "Пользователи Telegram"
        ordering = ["-created_at"]

    telegram_id = models.BigIntegerField("Telegram ID", primary_key=True)
    name = models.CharField("Имя", max_length=255, blank=True)
    workshop_address = models.CharField("Мастерская / адрес", max_length=255, blank=True)
    is_blocked = models.BooleanField("Заблокирован", default=False)
    created_at = models.DateTimeField("Создан", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    def __str__(self):
        return self.name or str(self.telegram_id)


class QueryLog(models.Model):
    class Meta:
        verbose_name = "Запрос пользователя"
        verbose_name_plural = "Запросы пользователей"
        ordering = ["-created_at"]

    user = models.ForeignKey(
        TelegramUser,
        on_delete=models.SET_NULL,
        related_name="queries",
        null=True,
        blank=True,
        verbose_name="Пользователь",
    )
    telegram_id = models.BigIntegerField("Telegram ID", db_index=True)
    query = models.CharField("Запрос", max_length=255)
    created_at = models.DateTimeField("Дата", auto_now_add=True)

    def __str__(self):
        return f"{self.telegram_id}: {self.query}"


class BotContent(models.Model):
    class Meta:
        verbose_name = "Текст бота"
        verbose_name_plural = "Тексты бота"

    code = models.CharField("Код", max_length=100, unique=True)
    title = models.CharField("Название", max_length=255)
    content = models.TextField("Текст", blank=True)
    updated_at = models.DateTimeField("Обновлен", auto_now=True)

    def __str__(self):
        return self.title


def normalize_text(text: str) -> str:
    return text.lower().replace(" ", "")
