import sqlite3
from pathlib import Path

from django.core.management.base import BaseCommand

from catalog.models import QueryLog, TelegramUser


class Command(BaseCommand):
    help = "Импортирует пользователей, блокировки и историю запросов из legacy SQLite."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default="user_queries.db",
            help="Путь к старой SQLite базе.",
        )

    def handle(self, *args, **options):
        source_path = Path(options["source"])
        if not source_path.exists():
            self.stderr.write(self.style.ERROR(f"Файл не найден: {source_path}"))
            return

        connection = sqlite3.connect(source_path)
        connection.row_factory = sqlite3.Row
        cursor = connection.cursor()

        blocked_ids = {
            row["user_id"]
            for row in cursor.execute("SELECT user_id FROM blocked_users")
        }

        imported_users = 0
        for row in cursor.execute("SELECT user_id, name, address FROM users"):
            TelegramUser.objects.update_or_create(
                telegram_id=row["user_id"],
                defaults={
                    "name": row["name"] or "",
                    "workshop_address": row["address"] or "",
                    "is_blocked": row["user_id"] in blocked_ids,
                },
            )
            imported_users += 1

        for blocked_id in blocked_ids:
            TelegramUser.objects.update_or_create(
                telegram_id=blocked_id,
                defaults={"is_blocked": True},
            )

        imported_queries = 0
        for row in cursor.execute("SELECT user_id, query FROM queries ORDER BY id"):
            user = TelegramUser.objects.filter(telegram_id=row["user_id"]).first()
            QueryLog.objects.create(
                user=user,
                telegram_id=row["user_id"],
                query=row["query"],
            )
            imported_queries += 1

        connection.close()
        self.stdout.write(
            self.style.SUCCESS(
                f"Импорт завершен: пользователей обработано {imported_users}, запросов импортировано {imported_queries}."
            )
        )
