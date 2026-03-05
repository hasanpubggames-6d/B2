from aiogram import Bot, types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy.future import select
from database.models import Channel, Setting
from database.db_manager import async_session

class SubscriptionManager:
    @staticmethod
    async def check_subscription(bot: Bot, user_id: int) -> bool:
        """
        Check if user is subscribed to all active channels.
        """
        async with async_session() as session:
            # Check if subscription system is enabled
            setting_result = await session.execute(select(Setting).where(Setting.key == "subscription_enabled"))
            setting = setting_result.scalar_one_or_none()
            if setting and setting.value == "false":
                return True
            
            # Get all active channels
            result = await session.execute(select(Channel).where(Channel.is_active == True))
            channels = result.scalars().all()
            
            if not channels:
                return True
            
            for channel in channels:
                try:
                    member = await bot.get_chat_member(chat_id=channel.channel_id, user_id=user_id)
                    if member.status in ["left", "kicked"]:
                        return False
                except Exception as e:
                    print(f"Error checking channel {channel.channel_id}: {e}")
                    # If bot is not admin in channel, we might skip or handle accordingly
                    continue
            
            return True

    @staticmethod
    async def get_subscription_keyboard() -> types.InlineKeyboardMarkup:
        """
        Generate keyboard with channel links.
        """
        async with async_session() as session:
            result = await session.execute(select(Channel).where(Channel.is_active == True))
            channels = result.scalars().all()
            
            builder = InlineKeyboardBuilder()
            for channel in channels:
                builder.row(types.InlineKeyboardButton(text=channel.title, url=channel.invite_link))
            
            builder.row(types.InlineKeyboardButton(text="Check Subscription", callback_data="check_sub"))
            return builder.as_markup()
