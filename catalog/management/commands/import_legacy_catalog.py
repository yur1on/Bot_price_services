from decimal import Decimal

from django.core.management.base import BaseCommand

from baza_glass import prices
from baza_lcd import displays
from baza_lcd_kit import displays1
from catalog.models import Device, DisplayOption


class Command(BaseCommand):
    help = "Импортирует текущий каталог из legacy-словарей в Django БД."

    def handle(self, *args, **options):
        imported_devices = 0
        imported_displays = 0

        for model_name, price_info in prices.items():
            device, created = Device.objects.update_or_create(
                model_name=model_name,
                defaults={
                    "brand": model_name.split()[0] if model_name else "",
                    "glass_replacement_price": Decimal(str(price_info["replacement"])),
                    "glass_replacement_without_disassembly_price": Decimal(str(price_info["without_disassembly"])),
                    "turnkey_price": Decimal(str(price_info["key"])) if price_info["key"] > 0 else None,
                    "is_active": True,
                },
            )
            imported_devices += int(created)

            for display_type, source in (
                (DisplayOption.DisplayType.ORIGINAL, displays),
                (DisplayOption.DisplayType.COPY, displays1),
            ):
                display_info = source.get(model_name)
                if not display_info:
                    continue

                DisplayOption.objects.update_or_create(
                    device=device,
                    display_type=display_type,
                    defaults={
                        "price": Decimal(str(display_info["price"])),
                        "stock": int(display_info["stock"]),
                    },
                )
                imported_displays += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершен: устройств создано {imported_devices}, записей дисплеев обновлено/создано {imported_displays}."
            )
        )
