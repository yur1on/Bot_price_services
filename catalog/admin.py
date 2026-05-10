from django.contrib import admin

from .models import BotContent, Device, DisplayOption, QueryLog, TelegramUser


class DisplayOptionInline(admin.TabularInline):
    model = DisplayOption
    extra = 0


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = (
        "model_name",
        "brand",
        "glass_replacement_price",
        "glass_replacement_without_disassembly_price",
        "turnkey_price",
        "is_active",
    )
    list_filter = ("brand", "is_active")
    search_fields = ("model_name", "normalized_name")
    inlines = [DisplayOptionInline]


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


@admin.register(DisplayOption)
class DisplayOptionAdmin(admin.ModelAdmin):
    list_display = ("device", "display_type", "price", "stock")
    list_filter = ("display_type",)
    search_fields = ("device__model_name",)


@admin.register(BotContent)
class BotContentAdmin(admin.ModelAdmin):
    list_display = ("title", "code", "updated_at")
    search_fields = ("title", "code", "content")
