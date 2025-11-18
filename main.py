import os
import asyncio
import random
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
    # auto-delete timer (extra, pero 0 = off; main delete trigger = next new user)
    "welcome_autodelete_seconds": 0,
}

# In-memory lang muna (per chat_id)
GROUP_CONFIG: dict[int, dict] = {}


def get_config(chat_id: int) -> dict:
    cfg = GROUP_CONFIG.get(chat_id)
    if not cfg:
        cfg = DEFAULT_CONFIG.copy()
        # list ng mga welcome message IDs na dapat burahin pag may next na papasok
        cfg["welcome_msg_ids"] = []
        GROUP_CONFIG[chat_id] = cfg
    # siguraduhin may key kahit old version
    cfg.setdefault("welcome_msg_ids", [])
    return cfg


# ========= RANDOMIZED SEDUCTIVE LINES =========

WELCOME_LINES: list[str] = [
    "🫦 <b>{name}</b>… pasok ka na, wag ka lang lalabas nang hindi nagshashare. 😈",
    "😈 Hoy <b>{name}</b>, huwag kang mahiyâ… share ka muna bago ka magpakasarap dito.",
    "🔥 <b>{name}</b>, sakto dating mo… ready ka na ba sa kalat ng {chat}? Share muna ha.",
    "👀 <b>{name}</b>, napansin ka na namin… 3 shares lang, tapos buong {chat} na ang bahala sa’yo.",
    "💋 <b>{name}</b>, wag ka muna umupo — share ka muna, tapos saka ka namin papainitin.",
    "🥵 Teka lang <b>{name}</b>… bago ka mag-enjoy, pa-share ka muna ng channel ha.",
    "😏 <b>{name}</b>, hindi ka makakatakas… share mo muna ‘to 3x bago ka tuluyang malock-in.",
    "🖤 <b>{name}</b>, welcome sa {chat}… dito bawal KJ, share muna bago sumali sa kalat.",
    "🤭 <b>{name}</b> ah… ang lakas ng aura mo… pero mas lalakas ‘yan pag nag-share ka na. 😈",
    "💦 <b>{name}</b>, wag ka kabahan… simple lang rules: share 3x, then lapag na nang todo.",
    "🫦 <b>{name}</b>, tingin pa lang, alam na… pero prove it — share mo muna ‘to.",
    "🔥 <b>{name}</b>, welcome… dito nauubos ang hiya. Start muna sa share bago iba ang maubos. 😉",
    "😈 <b>{name}</b>, di ka aksidenteng napadpad dito… share mo muna ‘to para tuloy-tuloy na ang tadhana.",
    "👅 <b>{name}</b>, wag ka magpaka-innocent… alam namin kaya mong mag-share. 3x lang oh.",
    "💋 <b>{name}</b>, unlock muna bago ka magpakawild sa {chat}. Share button na, dali.",
    "🖤 <b>{name}</b>, dito sa {chat}, isang share mo lang… alam mo na sunod. Pero 3 muna ha. 😏",
    "🤤 <b>{name}</b>, hindi namin bibitawan ang pangalang ‘yan… lalo na pag nag-share ka na.",
    "😈 <b>{name}</b>, share mo ‘to sa iba… para hindi lang ikaw ang malalaglag dito.",
    "🔥 <b>{name}</b>, pinaghandaan ka ng {chat}… pero share mo muna, warm-up lang ‘yan.",
    "🫦 <b>{name}</b>, welcome sa problema mong masarap… pero start tayo sa share, hindi agad sa kalat.",
    "💦 <b>{name}</b>, kung mainit ka na ngayon… wait ka lang pag na-unlock mo na lahat.",
    "👀 <b>{name}</b>, kalma lang… isang share, dalawang share, tatlong share… tapos bahala na si {chat}.",
    "💋 <b>{name}</b>, wag mo pigilan sarili mo… share mo na ‘to, gusto ka rin naman ng channel eh.",
    "😏 <b>{name}</b>, nandito ka na, huwag ka na magpanggap. Share 3x tapos sabay-sabay na tayong maligaw.",
    "🔥 <b>{name}</b>, feel at home ka lang… pero ‘home’ starts after 3 shares. 😈",
    "🖤 <b>{name}</b>, ang sarap ng timing mo… sakto sa oras ng kalat. Share muna bago ka sumabay.",
    "🤭 <b>{name}</b>, kung ito pa lang kinikilig ka na… mas masarap pag na-unlock mo na lahat.",
    "😈 <b>{name}</b>, rules are simple: share, enjoy, ulit. Start tayo sa first step — share mo na.",
    "🫦 <b>{name}</b>, wag mo nang hintayin ma-miss out ka… share mo na ‘to bago ka pa namin hanapin.",
    "💋 <b>{name}</b>, welcome sa {chat}… kung ready ka na, alam mo na gagawin: pindutin ang share. 😏",
]


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
        text=f"𝙎𝙃𝘼𝙍𝙀({share_count}/3)",
        url=f"https://t.me/share/url?url={encoded_link}&text=𝑷𝑰𝑵𝑨𝒀%20𝑳𝑨𝑷𝑨𝑮𝑨𝑵%20𝑻𝑨𝑹𝑨💦",
    )

    join_btn = InlineKeyboardButton(
        text="𝗝𝗢𝗜𝗡 𝗡𝗢𝗪",
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
    """Optional helper kung gusto mong auto-delete mga messages (extra, di required)."""
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
        "ma-auto-clean ko yung system notes at mag-welcome sa mga bagong papasok. 🤖"
    )


@dp.message(F.new_chat_members)
async def on_new_members(message: Message):
    chat_id = message.chat.id
    cfg = get_config(chat_id)

    # 1) Delete 'X joined the group' system message
    if cfg["delete_join_system_msg"]:
        with suppress(Exception):
            await bot.delete_message(chat_id, message.message_id)

    if not cfg["welcome_enabled"]:
        return

    chat_title = message.chat.title or "this chat"

    # 2) BURAHIN LAHAT NG LUMANG WELCOME MESSAGES bago gumawa ng bago
    old_ids = cfg.get("welcome_msg_ids", [])
    for mid in old_ids:
        with suppress(Exception):
            await bot.delete_message(chat_id, mid)
    cfg["welcome_msg_ids"] = []

    # 3) For EACH new member, send sariling welcome
    for user in message.new_chat_members:
        # "name lang" — no @username
        name = user.full_name

        # optional sticker
        if WELCOME_STICKER_ID:
            with suppress(Exception):
                await bot.send_sticker(chat_id, WELCOME_STICKER_ID)

        # random seductive line
        line_template = random.choice(WELCOME_LINES)
        text = line_template.format(name=name, chat=chat_title)

        sent = await bot.send_message(
            chat_id,
            text,
            reply_markup=make_lock_keyboard(share_count=0),
        )

        # i-store yung ID para mabura sa susunod na may papasok
        cfg["welcome_msg_ids"].append(sent.message_id)

        # extra option: auto-delete after X seconds (optional lang)
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
