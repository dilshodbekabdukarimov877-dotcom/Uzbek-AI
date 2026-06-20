import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.types import Message
from aiogram.filters import CommandStart
from anthropic import AsyncAnthropic
from aiohttp import web

# Logging
logging.basicConfig(level=logging.INFO)

# Tokenlar (Render panelida qoladi, ularga tegmang)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") # Bu yerda sizning OpenRouter API kalitingiz turibdi

if not TELEGRAM_TOKEN or not CLAUDE_API_KEY:
    raise ValueError("TELEGRAM_TOKEN yoki CLAUDE_API_KEY topilmadi!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# MANA SHU YERDA: OpenRouter manzili va kerakli sarlavhalarni ko'rsatamiz
claude_client = AsyncAnthropic(
    api_key=CLAUDE_API_KEY,
    base_url="https://openrouter.ai/api/v1",
    default_headers={
        "HTTP-Referer": "https://render.com", # Majburiy emas, lekin OpenRouter uchun yaxshi
        "X-Title": "Telegram Claude Bot"
    }
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}!\n"
        f"Men OpenRouter orqali Claude modelida ishlaydigan botman."
    )

@dp.message()
async def claude_ai_handler(message: Message) -> None:
    waiting_message = await message.answer("💡 <i>O'ylayapman...</i>", parse_mode="HTML")
    try:
        # OpenRouter'dagi aniq Claude model nomi (Model nomini o'zgartirdik!)
        response = await claude_client.messages.create(
            model="anthropic/claude-3.5-sonnet",
            max_tokens=2000,
            messages=[{"role": "user", "content": message.text}]
        )
        reply_text = response.content[0].text
        await waiting_message.delete()
        await message.answer(reply_text)
    except Exception as e:
        logging.error(f"Xatolik: {e}")
        await waiting_message.delete()
        await message.answer("❌ Xatolik yuz berdi. Birozdan so'ng urinib ko'ring.")

# Veb-ping xizmati Render uchun
async def handle_ping(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get('/', handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()

async def main() -> None:
    asyncio.create_task(start_web_server())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
