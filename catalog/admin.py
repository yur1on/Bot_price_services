from django import forms
from django.contrib import admin

from .models import BotContent, Device, DisplayOption, QueryLog, TelegramUser


class DeviceAdminForm(forms.ModelForm):
    class Meta:
        model = Device
        fields = (
            "model_name",
            "glass_replacement_price",
            "glass_replacement_without_disassembly_price",
            "turnkey_price",
            "needs_risk_confirmation",
            "success_rate",
            "is_active",
            "brand",
        )


class DisplayOptionInline(admin.TabularInline):
    model = DisplayOption
    extra = 0
    verbose_name = "Дисплей"
    verbose_name_plural = "Дисплеи в наличии"
    fields = ("display_type", "price", "stock")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    form = DeviceAdminForm
    list_display = (
        "model_name",
        "glass_replacement_price",
        "glass_replacement_without_disassembly_price",
        "turnkey_price",
        "needs_risk_confirmation",
        "success_rate",
        "is_active",
    )
    list_filter = ("is_active", "brand")
    search_fields = ("model_name", "normalized_name")
    inlines = [DisplayOptionInline]
    fieldsets = (
        (
            None,
            {
                "fields": (
                    "model_name",
                    "glass_replacement_price",
                    "glass_replacement_without_disassembly_price",
                    "turnkey_price",
                    "needs_risk_confirmation",
                    "success_rate",
                    "is_active",
                )
            },
        ),
        (
            "Дополнительно",
            {
                "fields": ("brand",),
                "classes": ("collapse",),
                "description": "Бренд можно не заполнять: он подставится автоматически из названия модели.",
            },
        ),
    )


@admin.register(TelegramUser)
class TelegramUserAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "name", "workshop_address", "is_blocked", "created_at")
    list_editable = ("is_blocked",)
    list_filter = ("is_blocked",)
    search_fields = ("telegram_id", "name", "workshop_address")


@admin.register(QueryLog)
class QueryLogAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "query", "created_at")
    search_fields = ("telegram_id", "query")
    list_filter = ("created_at",)


@admin.register(BotContent)
class BotContentAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "updated_at")
    search_fields = ("title", "code", "content")
