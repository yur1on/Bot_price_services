import logging
import os
from html import escape

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "newbot.settings")

import django
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ParseMode
from aiogram.utils import executor
from asgiref.sync import sync_to_async

from config import ADMIN_ID, API_TOKEN

django.setup()

from catalog.models import BotContent, QueryLog, TelegramUser, normalize_text
from catalog.services import search_devices_with_total


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
PAGE_SIZE = 4
pagination_state = {}

bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


def contains_cyrillic(text):
    return any("\u0400" <= char <= "\u04FF" for char in text)


def format_price(value):
    if value is None:
        return "договорная"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def get_more_inline_keyboard(offset: int):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("Еще 4", callback_data=f"more:{offset}"))
    return keyboard


@sync_to_async
def log_user_query(user_id, query):
    user = TelegramUser.objects.filter(telegram_id=user_id).first()
    QueryLog.objects.create(user=user, telegram_id=user_id, query=query)


@sync_to_async
def is_user_blocked(user_id):
    return TelegramUser.objects.filter(telegram_id=user_id, is_blocked=True).exists()


@sync_to_async
def is_user_authorized(user_id):
    return TelegramUser.objects.filter(telegram_id=user_id).exists()


@sync_to_async
def block_user_by_id(user_id):
    TelegramUser.objects.update_or_create(
        telegram_id=user_id,
        defaults={"is_blocked": True},
    )


@sync_to_async
def unblock_user_by_id(user_id):
    TelegramUser.objects.filter(telegram_id=user_id).update(is_blocked=False)


@sync_to_async
def ensure_user_exists(user_id, username, first_name, last_name):
    full_name = " ".join(part for part in [first_name, last_name] if part).strip()
    TelegramUser.objects.update_or_create(
        telegram_id=user_id,
        defaults={
            "name": full_name or username or "",
        },
    )


@sync_to_async
def get_matched_devices(user_input, offset=0):
    return search_devices_with_total(user_input, limit=PAGE_SIZE, offset=offset)


@sync_to_async
def get_info_text():
    content, _ = BotContent.objects.get_or_create(
        code="info",
        defaults={
            "title": "Информация",
            "content": "Текст для кнопки 'Инфо' пока не заполнен. Его можно изменить в Django-админке.",
        },
    )
    return content.content.strip() or "Текст для кнопки 'Инфо' пока не заполнен."


@dp.message_handler(commands=["block"], user_id=ADMIN_ID)
async def block_user(message: types.Message):
    try:
        user_id_to_block = int(message.text.split()[1])
        await block_user_by_id(user_id_to_block)
        await message.reply(f"Пользователь с ID {user_id_to_block} заблокирован.")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /block <user_id>")


@dp.message_handler(commands=["unblock"], user_id=ADMIN_ID)
async def unblock_user_command(message: types.Message):
    try:
        user_id_to_unblock = int(message.text.split()[1])
        await unblock_user_by_id(user_id_to_unblock)
        await message.reply(f"Пользователь с ID {user_id_to_unblock} разблокирован.")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /unblock <user_id>")


@dp.message_handler(commands=["info"])
async def show_info(message: types.Message):
    info_text = await get_info_text()
    await message.reply(info_text)


@dp.callback_query_handler(lambda call: call.data.startswith("more:"))
async def show_more_results(call: types.CallbackQuery):
    user_id = call.from_user.id
    state = pagination_state.get(user_id)
    if not state:
        await call.answer("Сначала выполните новый поиск.", show_alert=True)
        return

    expected_offset = int(call.data.split(":", 1)[1])
    if state["offset"] != expected_offset:
        await call.answer("Эта кнопка уже устарела. Выполните поиск заново.", show_alert=True)
        return

    await call.answer()
    await send_search_results(
        message=call.message,
        user_input=state["query"],
        offset=state["offset"],
        is_followup=True,
    )


async def send_search_results(message: types.Message, user_input: str, offset: int = 0, is_followup: bool = False):
    matched_devices, total = await get_matched_devices(user_input, offset)
    user_id = message.chat.id

    if matched_devices:
        response_parts = []
        for device in matched_devices:
            lines = [
                f"📱 <b>Модель:</b> {escape(device.model_name)}",
                f"🔧 <b>Только переклейка стекла:</b> {format_price(device.glass_replacement_price)}$",
                f"🛠 <b>Выклейка и переклейка:</b> {format_price(device.glass_replacement_without_disassembly_price)}$",
            ]
            if device.turnkey_price is not None:
                lines.append(f"✅ <b>Переклейка под ключ:</b> {format_price(device.turnkey_price)}$")
            else:
                lines.append("✅ <b>Переклейка под ключ:</b> договорная")

            if device.needs_risk_confirmation:
                if device.success_rate is not None:
                    lines.append(
                        f"⚠️ <b>Согласовывайте риски с клиентом.</b> "
                        f"Процент успеха: <b>{device.success_rate}%</b>"
                    )
                else:
                    lines.append("⚠️ <b>Согласовывайте риски с клиентом</b>")

            display_lines = []
            for display in device.display_options.all():
                if display.stock <= 0:
                    continue
                display_label = "Оригинал" if display.display_type == "original" else "Копия"
                display_lines.append(f"{display_label}: {format_price(display.price)}$ ({display.stock} шт.)")

            if display_lines:
                lines.append("")
                lines.append("🖥 <b>Дисплеи в наличии:</b>")
                lines.extend(display_lines)

            response_parts.append("\n".join(lines))

        shown_from = offset + 1
        shown_to = offset + len(matched_devices)
        header = ""
        if total > PAGE_SIZE:
            header = f"Найдено: <b>{total}</b>. Показаны результаты <b>{shown_from}-{shown_to}</b>.\n\n"

        response = header + "\n\n━━━━━━━━━━━━━━\n\n".join(response_parts)

        has_more = shown_to < total
        inline_keyboard = None
        if has_more:
            response += "\n\n<b>Можно посмотреть следующие 4 по кнопке ниже или введите модель точнее.</b>"
            pagination_state[user_id] = {"query": user_input, "offset": shown_to}
            inline_keyboard = get_more_inline_keyboard(shown_to)
        else:
            pagination_state.pop(user_id, None)

        response += "\n\n📍 <b>Гагарина 55</b>\n✉️ @Yur1on"
        await message.reply(
            response,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_keyboard,
        )
        return

    pagination_state.pop(user_id, None)
    normalized_input = normalize_text(user_input)
    logger.info("No matches for query '%s' (%s)", user_input, normalized_input)
    response = (
        "Нет информации по данной модели.\n"
        "Попробуйте изменить поиск сократив его до модели.\n"
        "Пример: a50, redmi 12"
    )
    if is_followup:
        response = "Больше результатов нет. Введите модель точнее для нового поиска."
    await message.reply(response, parse_mode=ParseMode.HTML)


@dp.message_handler(commands=["start"])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    await ensure_user_exists(
        user_id=user_id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        last_name=message.from_user.last_name,
    )

    if await is_user_blocked(user_id):
        await message.reply(
            "Для доступа к прайсу напишите @Yur1on.\n"
            "После проверки вас добавят к пользованию ботом.",
        )
        return

    await message.reply(
        "Введи модель телефона, чтобы узнать стоимость замены стекла.",
    )




@dp.message_handler()
async def price_query(message: types.Message):
    user_id = message.from_user.id

    if await is_user_blocked(user_id):
        await message.reply(
            "Для доступа к прайсу напишите @Yur1on.\n"
            "После проверки вас добавят к пользованию ботом.",
        )
        return

    if not await is_user_authorized(user_id):
        await message.reply(
            "Сначала нажмите /start, чтобы авторизоваться и начать работу с ботом.",
        )
        return

    user_input = message.text.strip().lower()

    if contains_cyrillic(user_input):
        await message.reply("Пожалуйста, введите модель телефона на английском языке.")
        return

    typo_checks = {
        "techno": "tecno",
        "comon": "camon",
        "realmi": "realme",
        "tekno": "tecno",
    }
    for wrong, correct in typo_checks.items():
        if wrong in user_input:
            await message.reply(
                f"❗Повторите запрос исправив слово <b>'{wrong}'</b> на правельное написание <b>{correct}</b>.",
                parse_mode=ParseMode.HTML,
            )
            return

    if "+" in user_input:
        await message.reply(
            "❗Повторите запрос исправив знак <b>'+'</b> на слово <b>plus</b>.",
            parse_mode=ParseMode.HTML,
        )
        return

    await log_user_query(user_id, user_input)
    await send_search_results(message=message, user_input=user_input, offset=0)


if __name__ == "__main__":
    executor.start_polling(dp, skip_updates=True)
