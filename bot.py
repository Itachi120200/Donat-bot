import asyncio
import logging
import sqlite3
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config
from database import init_db

logging.basicConfig(level=logging.INFO)
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def get_db():
    return sqlite3.connect('bot_database.db')

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Do'konni ochish (Mini App)", web_app=WebAppInfo(url="https://sizning-sayt.uz/webapp/index.html"))],
        [InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="my_orders"), InlineKeyboardButton(text="ℹ️ Yordam", callback_data="help")]
    ])
    if message.from_user.id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Admin Panel", callback_data="admin_panel")])

    await message.answer(
        f"👋 Assalomu alaykum, <b>{message.from_user.first_name}</b>!\n\n"
        "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar, Telegram xizmatlari va NFT'larni eng qulay narxlarda xarid qiling.\n\n"
        "Do'konni ochish uchun pastdagi tugmani bosing:",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "my_orders")
async def my_orders_handler(callback: types.CallbackQuery):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, amount, status FROM orders WHERE user_id = ?", (callback.from_user.id,))
        orders = cursor.fetchall()
    except sqlite3.OperationalError:
        orders = []
    conn.close()

    if not orders:
        text = "📦 Sizda hali buyurtmalar yo'q."
    else:
        text = "📦 **Sizning buyurtmalaringiz:**\n\n"
        for o in orders:
            text += f"• ID: {o[0]} | Summa: {o[1]} so'm | Holati: {o[2]}\n"

    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Qaytish", callback_data="back_home")]]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "help")
async def help_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "ℹ️ **Yordam markazi**\n\n"
        "Botdan foydalanishda muammo yuzaga kelsa yoki savollaringiz bo'lsa, adminlarimizga murojaat qiling:\n"
        "📞 Admin bilan bog'lanish",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Qaytish", callback_data="back_home")]]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return await callback.answer("Siz admin emassiz!", show_alert=True)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
        [InlineKeyboardButton(text="📢 Xabar yuborish (Broadcast)", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_home")]
    ])
    await callback.message.edit_text("⚙️ <b>Admin Panel</b>\nKerakli bo'limni tanlang:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: types.CallbackQuery):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM orders")
        total_orders = cursor.fetchone()[0]
        cursor.execute("SELECT SUM(amount) FROM orders WHERE status='bajarildi'")
        total_sum = cursor.fetchone()[0] or 0
    except sqlite3.OperationalError:
        total_orders = 0
        total_sum = 0
    conn.close()

    await callback.message.edit_text(
        f"📊 <b>Statistika:</b>\n\n"
        f"• Jami buyurtmalar: {total_orders}\n"
        f"• Muvaffaqiyatli savdo: {total_sum:,.0f} so'm",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Qaytish", callback_data="admin_panel")]]),
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: types.CallbackQuery):
    await callback.answer("Broadcast xizmati tez orada qo'shiladi!", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
    await callback.message.delete()
    await cmd_start(callback.message)

# --- Render uchun veb-server qismi ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
# -------------------------------------

async def main():
    init_db()
    print("Bot ishga tushdi...")
    await asyncio.gather(
        web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    asyncio.run(main())
    
