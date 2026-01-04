import logging
import asyncio
import sqlite3
import time
import os

from telethon import TelegramClient, events, Button, functions
from telethon.errors import UserNotParticipantError

# -----------------------------
# تنظیمات
# -----------------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 586732691

API_ID = 2040
API_HASH = "b18441a1ff607e10a989891a5462e627"

CHANNELS_TO_CHECK = ["monsmain", "earn_monsmain", "sponsoracb"]

# -----------------------------
# اتصال به تلگرام
# -----------------------------
bot = TelegramClient("acb_session", API_ID, API_HASH)
bot.start(bot_token=8293405809:AAECcVlJ5Ausp_uQSHOxsUXereyAso7YuYA)

logging.basicConfig(level=logging.INFO)

# -----------------------------
# دیتابیس SQLite
# -----------------------------
DB_NAME = "acb.db"

def get_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,
            points INTEGER DEFAULT 0,
            invited_by INTEGER,
            join_date TEXT
        )
    """)
    conn.commit()
    conn.close()

def add_or_update_user(user_id, first_name, username, invited_by=None):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (user_id,)).fetchone()

    if not user:
        conn.execute(
            "INSERT INTO users VALUES (?, ?, ?, 0, ?, ?)",
            (user_id, first_name, username, invited_by, time.strftime("%Y-%m-%d"))
        )
        if invited_by:
            conn.execute(
                "UPDATE users SET points = points + 2 WHERE user_id=?",
                (invited_by,)
            )
    else:
        conn.execute(
            "UPDATE users SET first_name=?, username=? WHERE user_id=?",
            (first_name, username, user_id)
        )

    conn.commit()
    conn.close()

# -----------------------------
# جوین اجباری
# -----------------------------
async def check_joined(user_id):
    if user_id == ADMIN_ID:
        return []

    not_joined = []
    for ch in CHANNELS_TO_CHECK:
        try:
            entity = await bot.get_entity(ch)
            await bot(functions.channels.GetParticipantRequest(entity, user_id))
        except UserNotParticipantError:
            not_joined.append(ch)
        except:
            pass
    return not_joined

async def join_buttons(chs):
    buttons = [[Button.url(f"عضویت در {c}", f"https://t.me/{c}")] for c in chs]
    buttons.append([Button.inline("✅ عضو شدم", b"check_join")])
    return buttons

# -----------------------------
# /start
# -----------------------------
@bot.on(events.NewMessage(pattern="/start"))
async def start_handler(event):
    user = await event.get_sender()
    args = event.raw_text.split()

    inviter = int(args[1]) if len(args) > 1 and args[1].isdigit() else None
    if inviter == user.id:
        inviter = None

    add_or_update_user(user.id, user.first_name, user.username, inviter)

    await event.respond(
        "به بات ACB خوش اومدی 🌹",
        buttons=[[Button.inline("ورود به منو اصلی 🏠", b"menu")]]
    )

# -----------------------------
# Callback ها
# -----------------------------
@bot.on(events.CallbackQuery)
async def callbacks(event):
    uid = event.sender_id
    data = event.data.decode()

    if data == "check_join":
        missing = await check_joined(uid)
        if not missing:
            await event.answer("تایید شد ✅", alert=True)
            await show_menu(uid)
        else:
            await event.answer("هنوز عضو نیستی ❌", alert=True)
        return

    missing = await check_joined(uid)
    if missing:
        await event.respond("اول عضو شو 👇", buttons=await join_buttons(missing))
        return

    if data == "menu":
        await show_menu(uid)

# -----------------------------
# منوی اصلی
# -----------------------------
async def show_menu(uid):
    await bot.send_message(
        uid,
        "منوی اصلی 👇",
        buttons=[
            [Button.text("👤 حساب کاربری"), Button.text("🛍 سفارش‌ها")],
            [Button.text("🎒 کوله پشتی"), Button.text("🧰 جعبه ابزار")],
            [Button.text("📞 پشتیبانی")]
        ]
    )

# -----------------------------
# پیام‌های متنی
# -----------------------------
@bot.on(events.NewMessage)
async def message_handler(event):
    if event.raw_text.startswith("/"):
        return

    uid = event.sender_id
    missing = await check_joined(uid)
    if missing:
        await event.respond("برای ادامه عضو شو:", buttons=await join_buttons(missing))
        return

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE user_id=?", (uid,)).fetchone()
    conn.close()

    if event.raw_text == "👤 حساب کاربری":
        me = await bot.get_me()
        await event.respond(
            f"👤 نام: {user['first_name']}\n"
            f"🆔 آیدی: {uid}\n"
            f"💰 امتیاز: {user['points']}\n\n"
            f"🔗 لینک دعوت:\n"
            f"https://t.me/{me.username}?start={uid}"
        )

    elif event.raw_text == "📞 پشتیبانی":
        await event.respond("پشتیبانی: @SponsorACB_Admin")

# -----------------------------
# اجرا
# -----------------------------
if __name__ == "__main__":
    init_db()
    print("🚀 Bot is running on Railway")
    bot.run_until_disconnected()
