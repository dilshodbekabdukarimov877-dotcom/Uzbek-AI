]import os
import logging
import asyncio
import urllib.parse
from aiogram import Bot, Dispatcher, html, F
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, BufferedInputFile
from aiogram.filters import CommandStart, Command
from openai import AsyncOpenAI
import aiohttp
from aiohttp import web
from google import genai

# Logging
logging.basicConfig(level=logging.INFO)

# Tokenlar va API Kalitlar
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("CLAUDE_API_KEY") # OpenRouter API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")      # Google AI Studio API Key

if not TELEGRAM_TOKEN or not OPENROUTER_API_KEY:
    raise ValueError("TELEGRAM_TOKEN yoki CLAUDE_API_KEY topilmadi!")

if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY topilmadi!")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# 1. OpenRouter Klienti
openrouter_client = AsyncOpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://render.com",
        "X-Title": "Telegram Multi-Model Bot"
    }
)

# 2. Google AI Studio Klienti
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Xotira lug'atlari
chat_histories = {}
user_models = {}

# Modellarni aniqlab olamiz
MODEL_NEMOTRON = "nvidia/nemotron-3-ultra-550b-a55b:free"
MODEL_LING_VL = "inclusionai/ling-3.0-flash-vl:free"  # OpenRouter (InclusionAI)
MODEL_GEMINI_FLASH = "gemini-3.8-flash"                # Google AI Studio
MODEL_IMAGE_POLLINATIONS = "free-image-generator"

# Modellarni tanlash uchun tugmalar (Inline Keyboard)
def get_model_keyboard():
    buttons = [
        [InlineKeyboardButton(text="🚀 Nemotron 3 Ultra (OpenRouter)", callback_data="set_nemotron")],
        [InlineKeyboardButton(text="👁 Ling 3.0 Flash VL (OpenRouter Free)", callback_data="set_ling")],
        [InlineKeyboardButton(text="⚡ Gemini 3.8 Flash (Google AI Studio)", callback_data="set_gemini")],
        [InlineKeyboardButton(text="🎨 Bepul Rasm Generator (Pollinations)", callback_data="set_img_pollinations")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    user_id = message.from_user.id
    chat_histories[user_id] = []
    user_models[user_id] = MODEL_GEMINI_FLASH
    
    await message.answer(
        f"Salom, {html.bold(message.from_user.full_name)}!\n"
        f"Men multimodel botman. Hozirda sizda <b>Gemini 3.8 Flash</b> modeli faol.\n\n"
        f"🤖 Modelni o'zgartirish uchun: /model buyrug'ini yuboring.\n"
        f"🧹 Tarixni o'chirish uchun: /clear"
    )

@dp.message(Command("model"))
async def command_model_handler(message: Message) -> None:
    await message.answer("Quyidagi AI modellaridan birini tanlang:", reply_markup=get_model_keyboard())

@dp.message(Command("clear"))
async def command_clear_handler(message: Message) -> None:
    user_id = message.from_user.id
    chat_histories[user_id] = []
    await message.answer("🧹 Suhbatingiz tarixi tozalandi!")

# Callback Query handlerlari
@dp.callback_query(F.data == "set_nemotron")
async def process_set_nemotron(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_models[user_id] = MODEL_NEMOTRON
    chat_histories[user_id] = []
    await callback.message.edit_text("🚀 Model <b>Nemotron 3 Ultra</b> ga o'zgartirildi!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "set_ling")
async def process_set_ling(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_models[user_id] = MODEL_LING_VL
    chat_histories[user_id] = []
    await callback.message.edit_text("👁 Model <b>Ling 3.0 Flash VL</b> ga o'zgartirildi!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "set_gemini")
async def process_set_gemini(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_models[user_id] = MODEL_GEMINI_FLASH
    chat_histories[user_id] = []
    await callback.message.edit_text("⚡ Model <b>Gemini 3.8 Flash</b> ga o'zgartirildi!", parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "set_img_pollinations")
async def process_set_img_pollinations(callback: CallbackQuery):
    user_id = callback.from_user.id
    user_models[user_id] = MODEL_IMAGE_POLLINATIONS
    chat_histories[user_id] = []
    await callback.message.edit_text("🎨 Model <b>Pollinations AI (Rasm Generator)</b>ga o'zgartirildi!\n\n<i>Rasm ta'rifini yuboring.</i>", parse_mode="HTML")
    await callback.answer()

@dp.message()
async def ai_handler(message: Message) -> None:
    user_id = message.from_user.id
    
    if user_id not in chat_histories:
        chat_histories[user_id] = []
    if user_id not in user_models:
        user_models[user_id] = MODEL_GEMINI_FLASH
        
    current_model = user_models[user_id]

    # === BEPUL RASM GENERATSIYASI (Pollinations) ===
    if current_model == MODEL_IMAGE_POLLINATIONS:
        waiting_message = await message.answer("🎨 <i>Rasm chizilyapti, biroz kuting...</i>", parse_mode="HTML")
        try:
            encoded_prompt = urllib.parse.quote(message.text)
            image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?width=1024&height=1024&nologo=true"

            async with aiohttp.ClientSession() as session:
                async with session.get(image_url) as resp:
                    if resp.status == 200:
                        image_data = await resp.read()
                        photo_file = BufferedInputFile(image_data, filename="generated_image.jpg")
                        
                        await waiting_message.delete()
                        await message.answer_photo(photo=photo_file, caption=f"🖼 <b>Prompt:</b> {message.text}", parse_mode="HTML")
                    else:
                        await waiting_message.delete()
                        await message.answer("❌ Rasmni yuklashda xatolik yuz berdi. Qaytadan urinib ko'ring.")

        except Exception as e:
            logging.error(f"Rasm yaratishda xatolik: {e}")
            await waiting_message.delete()
            await message.answer(f"❌ Xatolik yuz berdi:\n<code>{str(e)[:150]}</code>", parse_mode="HTML")
        return

    # === MATN / CHAT MODELLARI ===
    waiting_message = await message.answer("💡 <i>O'ylayapman...</i>", parse_mode="HTML")
    
    chat_histories[user_id].append({"role": "user", "content": message.text})
    
    if len(chat_histories[user_id]) > 50:
        chat_histories[user_id] = chat_histories[user_id][-50:]

    try:
        # 1. Google AI Studio (Gemini 3.8 Flash)
        if current_model == MODEL_GEMINI_FLASH:
            response = await asyncio.to_thread(
                gemini_client.models.generate_content,
                model=MODEL_GEMINI_FLASH,
                contents=message.text
            )
            reply_text = response.text

        # 2. OpenRouter Modellari (Nemotron / Ling 3.0 Flash VL)
        else:
            response = await openrouter_client.chat.completions.create(
                model=current_model,
                messages=chat_histories[user_id],
                max_tokens=1500
            )
            reply_text = response.choices[0].message.content

        chat_histories[user_id].append({"role": "assistant", "content": reply_text})
        
        await waiting_message.delete()
        await message.answer(reply_text)
        
    except Exception as e:
        logging.error(f"AI Xatoligi: {e}")
        await waiting_message.delete()
        await message.answer(f"❌ Xatolik yuz berdi:\n<code>{str(e)[:150]}</code>", parse_mode="HTML")

# Veb-ping xizmati Render uchun
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
