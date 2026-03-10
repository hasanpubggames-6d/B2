import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from dotenv import load_dotenv
from database.db_manager import init_db, async_session
from database.models import User
from sqlalchemy.future import select
from handlers import admin_panel
from engines.ocr_engine import OCREngine
from engines.translation_engine import TranslationEngine
from core.subscription import SubscriptionManager
from core.limiter import RateLimiter

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
limiter = RateLimiter()

# Register Routers
dp.include_router(admin_panel.router)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    async with async_session() as session:
        # Check if user exists, if not create
        result = await session.execute(select(User).where(User.telegram_id == message.from_user.id))
        user = result.scalar_one_or_none()
        if not user:
            user = User(
                telegram_id=message.from_user.id,
                username=message.from_user.username,
                full_name=message.from_user.full_name
            )
            session.add(user)
            await session.commit()
    
    await message.answer("Welcome to Enterprise OCR & Translation Bot. Send an image to begin.")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    # 1. Check Subscription
    if not await SubscriptionManager.check_subscription(bot, message.from_user.id):
        keyboard = await SubscriptionManager.get_subscription_keyboard()
        await message.answer("You must subscribe to the following channels to use this bot:", reply_markup=keyboard)
        return

    # 2. Rate Limiting
    if not await limiter.is_allowed(message.from_user.id):
        await message.answer("Rate limit exceeded. Please wait a moment.")
        return

    # 3. Process Image
    status_msg = await message.answer("Processing image with AI Vision...")
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"temp_{photo.file_id}.jpg"
    await bot.download_file(file.file_path, file_path)
    
    try:
        # OCR
        ocr_text = await OCREngine.process_image(file_path)
        
        # Post-process OCR
        refined_text = await TranslationEngine.post_process_ai(ocr_text)
        
        # Translation (Default to Arabic for now)
        translated_text = await TranslationEngine.translate_text(refined_text, target_lang="Arabic")
        
        response = f"**Extracted Text:**\n{refined_text}\n\n**Translation:**\n{translated_text}"
        
        if len(response) > 4096:
            # Handle long text by sending as file
            with open(f"result_{photo.file_id}.txt", "w", encoding="utf-8") as f:
                f.write(response)
            await message.answer_document(types.FSInputFile(f"result_{photo.file_id}.txt"))
        else:
            await message.answer(response, parse_mode="Markdown")
            
    except Exception as e:
        await message.answer(f"An error occurred: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()

async def main():
    logging.basicConfig(level=logging.INFO)
    await init_db()
    print("Database initialized.")
    print("Bot is starting...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
