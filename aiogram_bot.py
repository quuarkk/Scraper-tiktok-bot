from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from tiktok_scraper import get_user_videos
import subprocess
import asyncio
import datetime
import os
from dotenv import load_dotenv  # Импорт для работы с .env

# Загружаем переменные из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")  # Получаем токен из .env

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словарь для хранения запланированных задач
scheduled_tasks = {}

class SetUsername(StatesGroup):
    waiting_for_username = State()

class ScheduleVideo(StatesGroup):
    waiting_for_username = State()
    waiting_for_time = State()

async def set_bot_commands():
    """Настройка команд для отображения в меню Telegram"""
    commands = [
        types.BotCommand(command="/start", description="Запустить бота"),
        types.BotCommand(command="/set_username", description="Получить ссылки на видео TikTok"),
        types.BotCommand(command="/schedule", description="Запланировать автоматическое скачивание видео"),
        types.BotCommand(command="/check", description="Проверить новые видео для последнего username")
    ]
    await bot.set_my_commands(commands)

# Функция для сохранения username в файл
def save_last_username(chat_id: int, username: str):
    with open(f'last_username_{chat_id}.txt', 'w') as f:
        f.write(username)

# Функция для чтения последнего username из файла
def load_last_username(chat_id: int) -> str:
    try:
        with open(f'last_username_{chat_id}.txt', 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("Используй /set_username для получения ссылок на видео, /schedule для автоматического скачивания по расписанию или /check для проверки новых видео последнего username.")

@dp.message(Command("set_username"))
async def cmd_set_username(message: types.Message, state: FSMContext):
    await message.answer("Введите username TikTok (без @):")
    await state.set_state(SetUsername.waiting_for_username)

@dp.message(SetUsername.waiting_for_username, F.text)
async def process_username(message: types.Message, state: FSMContext):
    await state.clear()
    username = message.text.strip()
    chat_id = message.chat.id
    save_last_username(chat_id, username)  # Сохраняем username в файл
    await message.answer(f"Поиск видео...")

    videos = get_user_videos(username, max_videos=10)
    if not videos:
        await message.answer("Не удалось найти видео. Проверьте username или попробуйте позже.")
        return

    history_file = f'history_{username}.txt'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            previous_links = set(f.read().splitlines())
    else:
        previous_links = set()

    current_links = videos[:10]
    new_links = [link for link in current_links if link not in previous_links]

    if not new_links:
        await message.answer(f"Новых видео среди первых 10 для @{username} нет.")
        return

    with open('video_urls.txt', 'w') as f:
        f.write('\n'.join(new_links))

    with open(history_file, 'w') as f:
        f.write('\n'.join(current_links[:10]))

    with open('chat_id.txt', 'w') as f:
        f.write(str(chat_id))

    await message.answer(f"Найдено {len(new_links)} новых видео среди первых 10 для @{username}.")

@dp.message(Command("schedule"))
async def cmd_schedule(message: types.Message, state: FSMContext):
    await message.answer("Введите username TikTok (без @):")
    await state.set_state(ScheduleVideo.waiting_for_username)

@dp.message(ScheduleVideo.waiting_for_username, F.text)
async def process_schedule_username(message: types.Message, state: FSMContext):
    username = message.text.strip()
    chat_id = message.chat.id
    save_last_username(chat_id, username)  # Сохраняем username в файл
    await state.update_data(username=username)
    await message.answer("Введите время для автоматического скачивания (в формате HH:MM, например, 14:30):")
    await state.set_state(ScheduleVideo.waiting_for_time)

@dp.message(ScheduleVideo.waiting_for_time, F.text)
async def process_schedule_time(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    time_str = message.text.strip()

    try:
        scheduled_time = datetime.datetime.strptime(time_str, "%H:%M").time()
    except ValueError:
        await message.answer("Неверный формат времени. Используйте HH:MM (например, 14:30).")
        await state.clear()
        return

    data = await state.get_data()
    username = data.get("username")

    if not username:
        await message.answer("Ошибка: username не был сохранен. Попробуйте снова с /schedule.")
        await state.clear()
        return

    scheduled_tasks[chat_id] = {"username": username, "time": scheduled_time}
    await message.answer(f"Задача запланирована: видео с @{username} будут проверяться каждый день в {time_str}.")

    await state.clear()
    asyncio.create_task(schedule_task(chat_id, username, scheduled_time))

@dp.message(Command("check"))
async def cmd_check(message: types.Message):
    chat_id = message.chat.id
    username = load_last_username(chat_id)  # Читаем username из файла
    if not username:
        await message.answer("Вы еще не вводили username. Используйте /set_username или /schedule.")
        return

    await message.answer(f"Поиск новых видео для @{username}...")
    videos = get_user_videos(username, max_videos=10)
    if not videos:
        await message.answer("Не удалось найти видео. Проверьте username или попробуйте позже.")
        return

    history_file = f'history_{username}.txt'
    if os.path.exists(history_file):
        with open(history_file, 'r') as f:
            previous_links = set(f.read().splitlines())
    else:
        previous_links = set()

    current_links = videos[:10]
    new_links = [link for link in current_links if link not in previous_links]

    if not new_links:
        await message.answer(f"Новых видео среди первых 10 для @{username} нет.")
        return

    with open('video_urls.txt', 'w') as f:
        f.write('\n'.join(new_links))

    with open(history_file, 'w') as f:
        f.write('\n'.join(current_links[:10]))

    with open('chat_id.txt', 'w') as f:
        f.write(str(chat_id))

    await message.answer(f"Найдено {len(new_links)} новых видео среди первых 10 для @{username}. Начинаю скачивание...")

    # Запускаем video_downloader.py для скачивания и отправки видео
    try:
        subprocess.run(["python", "video_downloader.py"], check=True)
        await message.answer("Скачивание и отправка видео завершены!")
    except subprocess.CalledProcessError as e:
        await message.answer(f"Ошибка при скачивании видео: {e}")

async def schedule_task(chat_id: int, username: str, scheduled_time: datetime.time):
    while True:
        now = datetime.datetime.now()
        scheduled_datetime = datetime.datetime.combine(now.date(), scheduled_time)

        if now > scheduled_datetime:
            scheduled_datetime += datetime.timedelta(days=1)

        wait_seconds = (scheduled_datetime - now).total_seconds()
        await asyncio.sleep(wait_seconds)

        videos = get_user_videos(username, max_videos=10)
        if not videos:
            await bot.send_message(chat_id, f"Не удалось найти видео для @{username}.")
            continue

        history_file = f'history_{username}.txt'
        if os.path.exists(history_file):
            with open(history_file, 'r') as f:
                previous_links = set(f.read().splitlines())
        else:
            previous_links = set()

        current_links = videos[:10]
        new_links = [link for link in current_links if link not in previous_links]

        if not new_links:
            await bot.send_message(chat_id, f"Новых видео среди первых 10 для @{username} нет.")
            continue

        with open('video_urls.txt', 'w') as f:
            f.write('\n'.join(new_links))

        with open(history_file, 'w') as f:
            f.write('\n'.join(current_links[:10]))

        with open('chat_id.txt', 'w') as f:
            f.write(str(chat_id))

        await bot.send_message(chat_id, f"Сохранено {len(new_links)} новых ссылок среди первых 10 для @{username}.")

async def main():
    await set_bot_commands()
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    finally:
        subprocess.run(["python", "video_downloader.py"])