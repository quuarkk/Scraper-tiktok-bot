import os
import asyncio
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import TelegramError
import yt_dlp
from dotenv import load_dotenv  # Импорт для работы с .env

# Загружаем переменные из .env
load_dotenv()
API_TOKEN = os.getenv("API_TOKEN")  # Получаем токен из .env

ydl_opts = {
    'format': 'best',
    'outtmpl': 'downloads/%(id)s.%(ext)s',
    'quiet': True,
}

async def download_video(url: str) -> str:
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            return filename
    except Exception as e:
        print(f"Ошибка загрузки: {e}")
        return None

async def send_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists('video_urls.txt'):
        await update.message.reply_text("Сначала выполните /set_username")
        return

    with open('video_urls.txt') as f:
        urls = f.read().splitlines()

    if not urls:
        await update.message.reply_text("Нет новых видео для скачивания.")
        return

    for i, url in enumerate(urls, 1):
        await update.message.reply_text(f"Скачиваю видео {i} из {len(urls)}...")
        video_path = await download_video(url)

        if video_path and os.path.exists(video_path):
            try:
                with open(video_path, 'rb') as f:
                    await context.bot.send_video(
                        chat_id=update.effective_chat.id,
                        video=f,
                        caption=f"Видео {i} из {len(urls)}"
                    )
                os.remove(video_path)
            except TelegramError as e:
                await update.message.reply_text(f"Ошибка отправки {i}: {e}")
        else:
            await update.message.reply_text(f"Ошибка загрузки видео {i}")

    await update.message.reply_text("Все видео отправлены!")
    with open('video_urls.txt', 'w') as f:
        f.write('')

async def auto_send(context: ContextTypes.DEFAULT_TYPE):
    await asyncio.sleep(10)

    try:
        with open('chat_id.txt') as f:
            chat_id = int(f.read().strip())
    except FileNotFoundError:
        print("Ошибка: chat_id не найден")
        return

    bot = Bot(token=API_TOKEN)
    try:
        update = Update(
            update_id=0,
            message=await bot.send_message(chat_id, "Обработка видео...")
        )
        await send_video(update, context)
        await asyncio.sleep(5)
        os.system("python aiogram_bot.py")
    except TelegramError as e:
        print(f"Ошибка инициализации: {e}")

def main():
    os.makedirs('downloads', exist_ok=True)
    application = Application.builder().token(API_TOKEN).build()
    application.add_handler(CommandHandler("send_video", send_video))
    application.add_error_handler(
        lambda u, c: print(f"Произошла ошибка: {c.error}")
    )
    application.job_queue.run_once(auto_send, 0)
    application.run_polling()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Бот остановлен")
    finally:
        for file in ['chat_id.txt']:
            if os.path.exists(file):
                os.remove(file)
        if os.path.exists('downloads'):
            for f in os.listdir('downloads'):
                os.remove(os.path.join('downloads', f))
            os.rmdir('downloads')