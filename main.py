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

# Tokenlar
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY")

if not TELEGRAM_TOKEN or not CLAUDE_API_KEY:
    raise ValueError("TELEGRAM_TOKEN yoki CLAUDE_API_KEY topilmadi!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# OpenRouter uchun standart Anthropic klienti sozlamasi
claude_client = AsyncAnthropic(
    api_key=CLAUDE_API_KEY,
    base_url="https://openrouter.ai/api/v1"
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}!\n"
        f"Men OpenRouter orqali Claude modelida ishlaydigan botman. Savolingizni bering!"
    )

@dp.message()
async def claude_ai_handler(message: Message) -> None:
    waiting_message = await message.answer("💡 <i>O'ylayapman...</i>", parse_mode="HTML")
    try:
        # OpenRouter uchun eng aniq va yangi model nomini yozamiz
        response = await claude_client.messages.create(
            model="anthropic/claude-sonnet-latest",
            max_tokens=2000,
            messages=[{"role": "user", "content": message.text}]
        )
        reply_text = response.content[0].text
        await waiting_message.delete()
        await message.answer(reply_text)
    except Exception as e:
        # Xatolikni Render loglarida aniq ko'rish uchun yozamiz
        logging.error(f"OpenRouter Xatoligi: {e}")
        await waiting_message.delete()
        await message.answer(f"❌ Xatolik yuz berdi: {str(e)[:100]}")

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
