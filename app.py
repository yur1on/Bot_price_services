
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
import sqlite3
from baza_glass import prices
from baza_lcd import displays
from baza_lcd_kit import displays1
from config import API_TOKEN, ADMIN_ID  # Добавляем ID администратора в конфигурационный файл

# Конфигурация логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# Подключение к базе данных SQLite
conn = sqlite3.connect('user_queries.db')
cursor = conn.cursor()

# Создание таблиц для хранения запросов, информации о пользователях и заблокированных пользователей
cursor.execute('''
CREATE TABLE IF NOT EXISTS queries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    query TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    name TEXT,
    address TEXT
)
''')

cursor.execute('''
CREATE TABLE IF NOT EXISTS blocked_users (
    user_id INTEGER PRIMARY KEY
)
''')

conn.commit()

# Логирование запросов пользователя
def log_user_query(user_id, query):
    cursor.execute('INSERT INTO queries (user_id, query) VALUES (?, ?)', (user_id, query))
    conn.commit()

# Проверка на наличие кириллических символов
def contains_cyrillic(text):
    return any('\u0400' <= char <= '\u04FF' for char in text)

# Нормализация текста
def normalize_text(text):
    return text.lower().replace(" ", "")

# Проверка, зарегистрирован ли пользователь
def is_user_registered(user_id):
    cursor.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

# Проверка, заблокирован ли пользователь
def is_user_blocked(user_id):
    cursor.execute('SELECT 1 FROM blocked_users WHERE user_id = ?', (user_id,))
    return cursor.fetchone() is not None

# Состояния для регистрации пользователя
class Registration(StatesGroup):
    name = State()
    address = State()

# Блокировка пользователя
@dp.message_handler(commands=['block'], user_id=ADMIN_ID)
async def block_user(message: types.Message):
    try:
        user_id_to_block = int(message.text.split()[1])
        cursor.execute('INSERT INTO blocked_users (user_id) VALUES (?)', (user_id_to_block,))
        conn.commit()
        await message.reply(f"Пользователь с ID {user_id_to_block} заблокирован.")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /block <user_id>")

# Разблокировка пользователя
def unblock_user(user_id):
    cursor.execute('DELETE FROM blocked_users WHERE user_id = ?', (user_id,))
    conn.commit()

# Обработчик команды /unblock
@dp.message_handler(commands=['unblock'], user_id=ADMIN_ID)
async def unblock_user_command(message: types.Message):
    try:
        user_id_to_unblock = int(message.text.split()[1])
        unblock_user(user_id_to_unblock)
        await message.reply(f"Пользователь с ID {user_id_to_unblock} разблокирован.")
    except (IndexError, ValueError):
        await message.reply("Используйте команду в формате: /unblock <user_id>")


# Регистрация пользователя
@dp.message_handler(commands=['register'], state='*')
async def register_user(message: types.Message):
    user_id = message.from_user.id
    if is_user_registered(user_id):
        await message.reply("Вы уже зарегистрированы.")
    else:
        await Registration.name.set()
        await message.reply("Введите Ваше имя:")

@dp.message_handler(state=Registration.name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text.strip()
    await Registration.next()
    await message.reply("Спасибо! Теперь введите название или адрес мастерской:\n\n<i>Ползователь с неверно введенными данными будет заблокирован</i>!", parse_mode=ParseMode.HTML)

@dp.message_handler(state=Registration.address)
async def process_address(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['address'] = message.text.strip()

    user_id = message.from_user.id
    name = data['name']
    address = data['address']

    cursor.execute('INSERT INTO users (user_id, name, address) VALUES (?, ?, ?)', (user_id, name, address))
    conn.commit()

    await state.finish()
    await message.reply("Регистрация завершена! Теперь вы можете узнать стоимость замены стекла.")

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    if is_user_blocked(user_id):
        await message.reply("Вы не можете использовать этого бота.\nВведенные данные при регистрации не соответствуют реальности,\n или Вы не являетесь моим клиентом \nДля разблокировки напишите @Yur1on")
        return

    if not is_user_registered(user_id):
        await message.reply("Для начала работы ответьте на 2 вопроса использовав команду /register.")
    else:
        await message.reply("Введи модель телефона, чтобы узнать стоимость замены стекла.")

# Обработчик запросов на стоимость замены стекла
@dp.message_handler()
async def price_query(message: types.Message):
    user_id = message.from_user.id

    if is_user_blocked(user_id):
        await message.reply("Вы не можете использовать этого бота.\nВведенные данные при регистрации не соответствуют реальности,\n или Вы не являетесь моим клиентом \nДля разблокировки напишите @Yur1on")
        return

    if not is_user_registered(user_id):
        await message.reply("Для начала работы ответьте на 2 вопроса использовав команду /register.")
        return

    user_input = message.text.strip().lower()

    # Проверка на наличие кириллических символов
    if contains_cyrillic(user_input):
        await message.reply("Пожалуйста, введите модель телефона на английском языке.")
        return

    # Проверка на слово "techno"
    if "techno" in user_input:
        await message.reply("❗Повторите запрос исправив слово <b>'techno'</b> на правельное написание <b>tecno</b>.", parse_mode=ParseMode.HTML)
        return
    # Проверка на слово "comon"
    if "comon" in user_input:
        await message.reply("❗Повторите запрос исправив слово <b>'comon'</b> на правельное написание <b>camon</b>.", parse_mode=ParseMode.HTML)
        return
    # Проверка на слово "realmi"
    if "realmi" in user_input:
        await message.reply("❗Повторите запрос исправив слово <b>'realmi'</b> на правельное написание <b>realme</b>.", parse_mode=ParseMode.HTML)
        return

    # Проверка на слово "tekno"
    if "tekno" in user_input:
        await message.reply("❗Повторите запрос исправив слово <b>'tekno'</b> на правельное написание <b>tecno</b>.", parse_mode=ParseMode.HTML)
        return

    # Проверка на символ "+"
    if "+" in user_input:
        await message.reply("❗Повторите запрос исправив знак <b>'+'</b> на слово <b>plus</b>.", parse_mode=ParseMode.HTML)
        return

    # Логирование запроса пользователя
    log_user_query(user_id, user_input)

    normalized_input = normalize_text(user_input)
    matched_models = []

    for model, details in prices.items():
        normalized_model = normalize_text(model)
        if normalized_input in normalized_model:
            matched_models.append((model, details))
            if len(matched_models) == 4:
                break

    if matched_models:
        response = ""
        for idx, (model, details) in enumerate(matched_models):
            display_info = displays.get(model, None)
            display_info1 = displays1.get(model, None)
            response += (
                f"*Модель:* __{model}__\n"
                f"*Только переклейка стекла:* {details['replacement']}$\n"
                f"*Выклейка и переклейка:* {details['without_disassembly']}$\n"
            )
            if details['key'] > 0:
                response += f"*Переклейка под ключ:* {details['key']}$\n\n"
            else:
                response += "*Переклейка под ключ:* договорная\n\n"

            if display_info and display_info['stock'] > 0:
                response += (
                    f"*🔘Дисплей в наличии:* оригинал\n"
                    f"*Стоимость дисплея:* {display_info['price']}$\n"
                    f"*Количество на складе:* {display_info['stock']}\n\n"
                )
            if display_info1 and display_info1['stock'] > 0:
                response += (
                    f"*Дисплей в наличии:* копия \n"
                    f"*Стоимость дисплея:* {display_info1['price']}$\n"
                    f"*Количество на складе:* {display_info1['stock']}\n\n"
                )

            # Добавляем разделительную линию, если это не последний результат
            if idx < len(matched_models) - 1:
                response += "------------------------------\n\n"

        # Добавляем строку с адресом только в конце последнего результата
        response += "*Гагарина 55, @Yur1on*\n\n"
    else:
        response = "Нет информации по данной модели.\nПопробуйте изменить поиск сократив его до модели.\nПример: a50, redmi 12"

    await message.reply(response, parse_mode=ParseMode.MARKDOWN)

if __name__ == '__main__':
    executor.start_polling(dp, skip_updates=True)



