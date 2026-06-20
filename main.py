import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.types import Message
from aiogram.filters import CommandStart
from openai import AsyncOpenAI
from aiohttp import web

# Logging
logging.basicConfig(level=logging.INFO)

# Tokenlar (Render panelidagiga tegmang)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY") # OpenRouter API key

if not TELEGRAM_TOKEN or not CLAUDE_API_KEY:
    raise ValueError("TELEGRAM_TOKEN yoki CLAUDE_API_KEY topilmadi!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# OpenAI klienti orqali OpenRouter-ga ulanish (Bu universal va eng xatosiz usul)
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=CLAUDE_API_KEY,
    default_headers={
        "HTTP-Referer": "https://render.com",
        "X-Title": "Telegram Claude Bot"
    }
)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}!\n"
        f"Men OpenRouter (Claude 3.5 Sonnet) botiman. Savolingizni bering!"
    )

@dp.message()
async def claude_ai_handler(message: Message) -> None:
    waiting_message = await message.answer("💡 <i>O'ylayapman...</i>", parse_mode="HTML")
    try:
        # OpenAI formati bo'yicha so'rov yuborish
        response = await client.chat.completions.create(
            model="anthropic/claude-3-5-sonnet",
            messages=[{"role": "user", "content": message.text}],
            max_tokens=2000
        )
        
        reply_text = response.choices[0].message.content
        await waiting_message.delete()
        await message.answer(reply_text)
        
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await waiting_message.delete()
        # Xatoni aniq ko'rish uchun foydalanuvchiga qisqa matn qaytaramiz
        await message.answer(f"❌ Xatolik yuz berdi:\n<code>{str(e)[:150]}</code>", parse_mode="HTML")

# Veb-ping xizmati Render uxlab qolmasligi uchun
async def handle_ping(request):
    return web.Response(text="Bot faol!")

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
