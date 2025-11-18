import os
import asyncio
from contextlib import suppress
from urllib.parse import quote  # para sa tamang pag-encode ng link

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties


# ========= ENV CONFIG =========

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN env variable is missing")

# Sticker file_id galing kay @idstickerbot (optional)
WELCOME_STICKER_ID = os.getenv("WELCOME_STICKER_ID")

# Ito yung channel / invite link na gusto mong i-unlock
CHANNEL_LINK = "https://t.me/+0qp1zIGHPlYwZTBl"


# ========= PER-GROUP CONFIG (SIMPLE) =========

DEFAULT_CONFIG = {
    "delete_join_system_msg": True,
    "delete_leave_system_msg": True,
    "delete_pinned_service_msg": True,
    "welcome_enabled": True,
    "welcome_text": (
        "🫦 <b>WELCOME!</b>\n\n"
        "🔐 <b>LOCKED CHANNEL MODE</b>\n"
        "To unlock the channel, <b>share</b> this channel 3 times using the button below,\n"
        "then tap <b>JOIN NOW</b> to continue. 😈🔥"
    ),
    "welcome_autodelete_seconds": 0,  # 0 = huwag auto-delete yung lock message
}

# In-memory lang muna (per chat_id)
GROUP_CONFIG: dict[int, dict] = {}


def get_config(chat_id: int) -> dict:
    cfg = GROUP_CONFIG.get(chat_id)
    if not cfg:
        cfg = DEFAULT_CONFIG.copy()
        cfg["last_lock_msg_id"] = None
        GROUP_CONFIG[chat_id] = cfg
    return cfg


# ========= BOT SETUP =========

bot = Bot(
    token=BOT_TOKEN,
    default=DefaultBotProperties(parse_mode="HTML"),
)
dp = Dispatcher()


# ========= KEYBOARD =========

def make_lock_keyboard(share_count: int = 0) -> InlineKeyboardMarkup:
    """
    Gumagawa ng SHARE + JOIN NOW buttons.
    Encode natin yung CHANNEL_LINK para hindi mawala yung '+' sa link.
    """
    encoded_link = quote(CHANNEL_LINK, safe="")

    share_btn = InlineKeyboardButton(
        text=f"𝙎𝙃𝘼𝙍𝙀({share_count}/3) - 𝑷𝑰𝑵𝑨𝒀 𝑳𝑨𝑷𝑨𝑮𝑨𝑵 𝑻𝑨𝑹𝑨💦",
        url=f"https://t.me/share/url?url={encoded_link}&text=Join%20this%20channel",
    )

    join_btn = InlineKeyboardButton(
        text="JOIN NOW",
        callback_data="join_now",
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [share_btn],
            [join_btn],
        ]
    )


# ========= HELPERS =========

async def delete_later(chat_id: int, msg_id: int, delay: int):
    """Optional helper kung gusto mong auto-delete mga messages."""
    try:
        await asyncio.sleep(delay)
        await bot.delete_message(chat_id, msg_id)
    except Exception:
        pass


# ========= HANDLERS =========

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Hi! Add me sa group as admin (may delete rights) para "
        "ma-auto-clean ko yung system notes at ma-send ko yung lock welcome message. 🤖"
    )


@dp.message(F.new_chat_members)
async def on_new_members(message: Message):
    chat_id = message.chat.id
    cfg = get_config(chat_id)

    # 1) Delete 'X joined the group' system message
    if cfg["delete_join_system_msg"]:
        with suppress(Exception):
            await bot.delete_message(chat_id, message.message_id)

    # 2) Delete previous lock message (para laging isa lang sa chat)
    last_id = cfg.get("last_lock_msg_id")
    if last_id:
        with suppress(Exception):
            await bot.delete_message(chat_id, last_id)

    if not cfg["welcome_enabled"]:
        return

    # 3) Optional: send sticker kung may WELCOME_STICKER_ID
    if WELCOME_STICKER_ID:
        with suppress(Exception):
            await bot.send_sticker(chat_id, WELCOME_STICKER_ID)

    # 4) Send new lock-style welcome message
    text = cfg["welcome_text"]

    sent = await bot.send_message(
        chat_id,
        text,
        reply_markup=make_lock_keyboard(share_count=0),
    )

    # 5) Save as last lock message
    cfg["last_lock_msg_id"] = sent.message_id

    # 6) Optional: auto-delete welcome lock message after X seconds
    seconds = cfg.get("welcome_autodelete_seconds", 0)
    if seconds and seconds > 0:
        asyncio.create_task(delete_later(chat_id, sent.message_id, seconds))


@dp.message(F.left_chat_member)
async def on_member_left(message: Message):
    chat_id = message.chat.id
    cfg = get_config(chat_id)

    if cfg["delete_leave_system_msg"]:
        with suppress(Exception):
            await bot.delete_message(chat_id, message.message_id)


@dp.message(F.pinned_message)
async def on_pinned(message: Message):
    chat_id = message.chat.id
    cfg = get_config(chat_id)

    if cfg["delete_pinned_service_msg"]:
        with suppress(Exception):
            await bot.delete_message(chat_id, message.message_id)


@dp.callback_query(F.data == "join_now")
async def on_join_now(cb: CallbackQuery):
    # Popup alert na lalabas sa user
    await cb.answer(
        "YOU NEED TO SHARE 3 TIMES TO UNLOCK THE CHANNEL",
        show_alert=True,
    )


# ========= ENTRYPOINT =========

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
