"""
БОТ С GROQ AI - БЕСПЛАТНЫЕ КАЧЕСТВЕННЫЕ КОНСПЕКТЫ
Использует Groq API (бесплатно, быстро, качественно!)

УСТАНОВКА:
1. pip install aiogram==3.7.0 yt-dlp groq
2. Получите бесплатный ключ Groq: https://console.groq.com/keys
3. Замените токены на строках 21-22
4. python groq_bot.py

GROQ API:
- 100% бесплатно (лимит: 30 запросов/минуту, 14400/день)
- Очень быстрый (быстрее OpenAI в 10 раз!)
- Качественные конспекты (модель Llama 3.3)
"""

import asyncio
import logging
import re
import time
import os
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
import yt_dlp
from groq import Groq

# ========================================
# ВСТАВЬТЕ ВАШИ ТОКЕНЫ (или используйте переменные окружения)
# ========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7668116650:AAHq7JCU0UhyqlNRUqEXkXQnIyUhnWcIeaU")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "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")

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# Инициализация Groq клиента
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != "YOUR_GROQ_API_KEY":
    try:
        groq_client = Groq(api_key=GROQ_API_KEY)
        logger.info("✅ Groq API подключен")
    except Exception as e:
        logger.error(f"❌ Ошибка подключения Groq: {e}")

last_request_time = 0
MIN_DELAY = 3


# ========================================
# ФУНКЦИИ ДЛЯ YOUTUBE
# ========================================

def is_youtube(url):
    return 'youtube.com' in url or 'youtu.be' in url


async def get_subs(url):
    """Получает субтитры с YouTube"""
    global last_request_time
    
    current_time = time.time()
    if current_time - last_request_time < MIN_DELAY:
        await asyncio.sleep(MIN_DELAY - (current_time - last_request_time))
    
    last_request_time = time.time()
    
    try:
        opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['ru', 'en'],
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': True,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            },
        }
        
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: extract_info(url, opts))
        
        if not info:
            return None, None, None, None
        
        subs = info.get('subtitles', {}) or info.get('automatic_captions', {})
        
        if not subs:
            return info.get('title'), None, info.get('duration', 0), None
        
        text = None
        lang = None
        
        for language in ['ru', 'en']:
            if language in subs:
                lang = language
                for fmt in subs[language]:
                    if fmt.get('ext') in ['vtt', 'srv3']:
                        try:
                            await asyncio.sleep(1)
                            with yt_dlp.YoutubeDL({'quiet': True, 'no_warnings': True}) as y:
                                text = y.urlopen(fmt['url']).read().decode('utf-8')
                                break
                        except Exception as e:
                            logger.error(f"Ошибка загрузки субтитров: {e}")
                            continue
                if text:
                    break
        
        if not text:
            return info.get('title'), None, info.get('duration', 0), None
        
        cleaned = clean_text(text)
        
        return info.get('title'), cleaned, info.get('duration', 0), lang
        
    except Exception as e:
        logger.error(f"Ошибка get_subs: {e}")
        return None, None, 0, None


def extract_info(url, opts):
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            return ydl.extract_info(url, download=False)
    except Exception as e:
        logger.error(f"Ошибка extract_info: {e}")
        return None


def clean_text(text):
    """Очистка субтитров"""
    text = re.sub(r'WEBVTT.*?\n\n', '', text, flags=re.DOTALL)
    text = re.sub(r'\d{2}:\d{2}:\d{2}\.\d{3}\s*-->\s*\d{2}:\d{2}:\d{2}\.\d{3}', '', text)
    text = re.sub(r'^\d+$', '', text, flags=re.MULTILINE)
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\n\s*\n', ' ', text)
    text = ' '.join(text.split())
    return text.strip()


# ========================================
# GROQ AI КОНСПЕКТ
# ========================================

async def create_ai_summary(title, text, duration, language='ru'):
    """Создаёт конспект с помощью Groq AI"""
    
    if not groq_client:
        logger.error("Groq API не настроен!")
        return None
    
    # Ограничиваем текст (Groq лимит ~8000 токенов)
    max_chars = 12000
    text_sample = text[:max_chars]
    
    # Промт для AI
    if language == 'ru':
        prompt = f"""Ты - эксперт по созданию образовательных конспектов. 

Название видео: {title}
Длительность: {duration // 60} мин {duration % 60} сек

Субтитры видео:
{text_sample}

Создай ПОДРОБНЫЙ структурированный конспект в следующем формате:

📖 ВВЕДЕНИЕ
(Кратко опиши о чём видео, 2-3 предложения)

💡 ОСНОВНЫЕ ИДЕИ И ТЕМЫ
(Перечисли 7-10 главных идей из видео, каждая идея - отдельный пункт с объяснением)

📋 ДЕТАЛИ И ПРИМЕРЫ
(Важные детали, примеры, факты, цифры из видео - 5-7 пунктов)

🔑 КЛЮЧЕВЫЕ ПОНЯТИЯ
(Перечисли основные термины и концепции через запятую)

🎯 ЗАКЛЮЧЕНИЕ
(Главный вывод видео, 2-3 предложения)

❓ ВОПРОСЫ ДЛЯ ПОВТОРЕНИЯ
(5-6 вопросов для проверки понимания материала)

Пиши подробно, структурированно, используй эмодзи. Все объяснения должны быть понятными и развёрнутыми."""
    else:
        prompt = f"""You are an expert at creating educational summaries.

Video title: {title}
Duration: {duration // 60} min {duration % 60} sec

Video transcript:
{text_sample}

Create a DETAILED structured summary in this format:

📖 INTRODUCTION
(Briefly describe what the video is about, 2-3 sentences)

💡 MAIN IDEAS AND TOPICS
(List 7-10 key ideas from the video, each idea as a separate point with explanation)

📋 DETAILS AND EXAMPLES
(Important details, examples, facts, numbers from the video - 5-7 points)

🔑 KEY CONCEPTS
(List main terms and concepts)

🎯 CONCLUSION
(Main takeaway from the video, 2-3 sentences)

❓ REVIEW QUESTIONS
(5-6 questions to check understanding)

Write in detail, structured, use emojis. All explanations should be clear and detailed."""
    
    try:
        # Запрос к Groq API
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": "Ты эксперт по созданию подробных образовательных конспектов. Создаёшь структурированные, понятные и полезные конспекты видео."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.7,
            max_tokens=4000,
            top_p=1,
        )
        
        summary = response.choices[0].message.content
        return summary
        
    except Exception as e:
        logger.error(f"Ошибка Groq AI: {e}")
        return None


# ========================================
# КОМАНДЫ БОТА
# ========================================

@dp.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "👋 <b>Привет! Я умный бот для конспектов YouTube!</b>\n\n"
        "📹 <b>Как использовать:</b>\n"
        "1. Отправь ссылку на YouTube видео\n"
        "2. Подожди 10-20 секунд\n"
        "3. Получи детальный AI-конспект\n\n"
        "📝 <b>Конспект включает:</b>\n"
        "• Введение\n"
        "• Основные идеи (7-10 пунктов)\n"
        "• Детали и примеры (5-7 пунктов)\n"
        "• Ключевые понятия\n"
        "• Заключение\n"
        "• Вопросы для повторения\n\n"
        "⚠️ Видео должно иметь субтитры!\n\n"
        "🚀 Отправь ссылку!",
        parse_mode="HTML"
    )


@dp.message()
async def handle_message(message: Message):
    url = message.text.strip()
    
    if not is_youtube(url):
        await message.answer("❌ Отправьте ссылку на YouTube!")
        return
    
    if not groq_client:
        await message.answer(
            "❌ <b>Groq API не настроен!</b>\n\n"
            "Получите бесплатный ключ:\n"
            "https://console.groq.com/keys",
            parse_mode="HTML"
        )
        return
    
    msg = await message.answer(
        "⏳ <b>Обрабатываю видео с AI...</b>\n\n"
        "Этап 1/3: Получаю субтитры...",
        parse_mode="HTML"
    )
    
    try:
        # Получаем субтитры
        title, text, duration, lang = await get_subs(url)
        
        if not title:
            await msg.edit_text(
                "❌ <b>Ошибка доступа к видео</b>\n\n"
                "Попробуйте через 1-2 минуты или другое видео!",
                parse_mode="HTML"
            )
            return
        
        if not text:
            await msg.edit_text(
                f"📹 <b>{title}</b>\n\n"
                "❌ Это видео не содержит субтитров!",
                parse_mode="HTML"
            )
            return
        
        # AI обработка
        await msg.edit_text(
            f"✅ Субтитры получены! ({len(text)} символов)\n\n"
            f"⏳ Этап 2/3: MindNotes AI анализирует видео...",
            parse_mode="HTML"
        )
        
        summary = await create_ai_summary(title, text, duration, lang or 'ru')
        
        if not summary:
            await msg.edit_text(
                "❌ <b>Ошибка AI обработки</b>\n\n"
                "Попробуйте ещё раз!",
                parse_mode="HTML"
            )
            return
        
        # Формируем результат
        await msg.edit_text(
            "✅ AI конспект готов!\n\n"
            "⏳ Этап 3/3: Отправляю...",
            parse_mode="HTML"
        )
        
        await asyncio.sleep(1)
        
        await msg.delete()
        
        # Формируем финальное сообщение
        final_message = f"🎬 <b>{title}</b>\n"
        final_message += f"⏱ {duration // 60} мин {duration % 60} сек\n\n"
        final_message += summary
        final_message += "\n\n🤖 <i>Создано с MindNotes AI </i>"
        
        # Разбиваем на части если длинный
        if len(final_message) > 4096:
            parts = []
            current_part = ""
            
            for line in final_message.split('\n'):
                if len(current_part) + len(line) + 1 > 4000:
                    parts.append(current_part)
                    current_part = line + '\n'
                else:
                    current_part += line + '\n'
            
            if current_part:
                parts.append(current_part)
            
            for i, part in enumerate(parts):
                if i == 0:
                    await message.answer(part, parse_mode="HTML")
                else:
                    await asyncio.sleep(0.5)
                    await message.answer(f"<i>Продолжение...</i>\n\n{part}", parse_mode="HTML")
        else:
            await message.answer(final_message, parse_mode="HTML")
        
        await message.answer(f"🔗 <a href='{url}'>Ссылка на видео</a>", parse_mode="HTML")
        
        logger.info(f"✅ AI конспект создан: {title}")
        
    except Exception as e:
        logger.error(f"Ошибка handle_message: {e}")
        await msg.edit_text(
            f"❌ <b>Произошла ошибка</b>\n\n"
            f"Попробуйте другое видео!",
            parse_mode="HTML"
        )


# ========================================
# ЗАПУСК
# ========================================

async def main():
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TOKEN_HERE":
        print("\n❌ Замените TELEGRAM_BOT_TOKEN!\n")
        return
    
    if not GROQ_API_KEY or GROQ_API_KEY == "YOUR_GROQ_API_KEY":
        print("\n❌ ВНИМАНИЕ: Groq API ключ не настроен!")
        print("Получите бесплатный ключ: https://console.groq.com/keys\n")
        return
    
    logger.info("🤖 MindNotes AI Bot запускается...")
    logger.info("✅ Бот успешно запущен!")
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при запуске: {e}")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⛔ Бот остановлен")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")