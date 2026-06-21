import os
import logging
import asyncio
from aiogram import Bot, Dispatcher, html
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI
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

# OpenAI klienti orqali OpenRouter
client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=CLAUDE_API_KEY,
    default_headers={
        "HTTP-Referer": "https://render.com",
        "X-Title": "Telegram Claude Bot"
    }
)

# Har bir foydalanuvchining chat tarixini saqlash uchun lug'at (Xotira)
# Tuzilishi: {user_id: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
chat_histories = {}

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    # Start bosilganda tarixni nollaymiz
    chat_histories[user_id] = []
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}!\n"
        f"Men suhbatni eslab qola oladigan Claude botman. Savolingizni bering!\n\n"
        f"🧹 Tarixni o'chirish uchun: /clear"
    )

@dp.message(Command("clear"))
async def command_clear_handler(message: Message) -> None:
    """ Chat tarixini tozalash funksiyasi """
    user_id = message.from_user.id
    chat_histories[user_id] = [] # Foydalanuvchi tarixini bo'shatamiz
    await message.answer("🧹 Suhbatingiz tarixi muvaffaqiyatli tozalandi! Bot sizni unutdi. Yangi savol berishingiz mumkin.")

@dp.message()
async def claude_ai_handler(message: Message) -> None:
    user_id = message.from_user.id
    
    # Agar foydalanuvchi birinchi marta yozayotgan bo'lsa, lug'atda joy ochamiz
    if user_id not in chat_histories:
        chat_histories[user_id] = []
        
    waiting_message = await message.answer("💡 <i>O'ylayapman...</i>", parse_mode="HTML")
    
    # Foydalanuvchining yangi xabarini tarixga qo'shamiz
    chat_histories[user_id].append({"role": "user", "content": message.text})
    
    # Kontekst juda uzayib ketsa OpenRouter-da xato bermasligi uchun 
    # oxirgi 20 ta xabarni cheklab turamiz
    if len(chat_histories[user_id]) > 20:
        chat_histories[user_id] = chat_histories[user_id][-20:]

    try:
        # OpenRouter-ga butun tarixni yuboramiz
        response = await client.chat.completions.create(
            model="openai/gpt-oss-120b:free",
            messages=chat_histories[user_id],
            max_tokens=99999
        )
        
        reply_text = response.choices[0].message.content
        
        # Botning javobini ham tarixga qo'shamiz (keyingi safar eslab turishi uchun)
        chat_histories[user_id].append({"role": "assistant", "content": reply_text})
        
        await waiting_message.delete()
        await message.answer(reply_text)
        
    except Exception as e:
        logging.error(f"Xatolik yuz berdi: {e}")
        await waiting_message.delete()
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
