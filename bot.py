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

# Tilni tanlash menyusi (/start)
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])
    await message.answer(
        "🌐 Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:",
        reply_markup=kb
    )

# Asosiy menyuni chiqaruvchi yordamchi funksiya
async def get_main_menu(user_id, lang):
    if lang == "uz":
        text = (
            f"👋 Assalomu alaykum!\n\n"
            "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar, Telegram xizmatlari va NFT'larni eng qulay narxlarda xarid qiling.\n\n"
            "Do'konni ochish uchun pastdagi tugmani bosing:"
        )
        btn_shop = "🛒 Do'konni ochish (Mini App)"
        btn_orders = "📦 Buyurtmalarim"
        btn_help = "ℹ️ Yordam"
        btn_admin = "⚙️ Admin Panel"
    elif lang == "ru":
        text = (
            f"👋 Здравствуйте!\n\n"
            "🎮 Добро пожаловать в <b>Ultimate Donat Bot</b>. Покупайте игры, Telegram-услуги и NFT по выгодным ценам.\n\n"
            "Нажмите кнопку ниже, чтобы открыть магазин:"
        )
        btn_shop = "🛒 Открыть магазин (Mini App)"
        btn_orders = "📦 Мои заказы"
        btn_help = "ℹ️ Помощь"
        btn_admin = "⚙️ Админ панель"
    else:
        text = (
            f"👋 Hello!\n\n"
            "🎮 Welcome to <b>Ultimate Donat Bot</b>. Buy games, Telegram services, and NFTs at the best prices.\n\n"
            "Click the button below to open the shop:"
        )
        btn_shop = "🛒 Open Shop (Mini App)"
        btn_orders = "📦 My Orders"
        btn_help = "ℹ️ Help"
        btn_admin = "⚙️ Admin Panel"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_shop, web_app=WebAppInfo(url="https://sizning-sayt.uz/webapp/index.html"))],
        [InlineKeyboardButton(text=btn_orders, callback_data=f"orders_{lang}"), InlineKeyboardButton(text=btn_help, callback_data=f"help_{lang}")]
    ])
    
    if user_id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_admin, callback_data=f"admin_{lang}")])

    return text, kb

# Til tanlanganda
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    text, kb = await get_main_menu(callback.from_user.id, lang)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

# Buyurtmalarim bo'limi
@dp.callback_query(F.data.startswith("orders_"))
async def my_orders_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, amount, status FROM orders WHERE user_id = ?", (callback.from_user.id,))
        orders = cursor.fetchall()
    except sqlite3.OperationalError:
        orders = []
    conn.close()

    if lang == "uz":
        if not orders:
            text = "📦 Sizda hali buyurtmalar yo'q."
        else:
            text = "📦 **Sizning buyurtmalaringiz:**\n\n"
            for o in orders:
                text += f"• ID: {o[0]} | Summa: {o[1]} so'm | Holati: {o[2]}\n"
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        if not orders:
            text = "📦 У вас пока нет заказов."
        else:
            text = "📦 **Ваши заказы:**\n\n"
            for o in orders:
                text += f"• ID: {o[0]} | Сумма: {o[1]} сум | Статус: {o[2]}\n"
        back_text = "🔙 Назад"
    else:
        if not orders:
            text = "📦 You have no orders yet."
        else:
            text = "📦 **Your Orders:**\n\n"
            for o in orders:
                text += f"• ID: {o[0]} | Amount: {o[1]} UZS | Status: {o[2]}\n"
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Yordam bo'limi
@dp.callback_query(F.data.startswith("help_"))
async def help_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    if lang == "uz":
        text = (
            "ℹ️ **Yordam markazi**\n\n"
            "Botdan foydalanishda muammo yuzaga kelsa, adminga murojaat qiling:\n"
            "📞 Admin: @evelineee_00"
        )
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = (
            "ℹ️ **Центр помощи**\n\n"
            "Если у вас возникли проблемы, обратитесь к администратору:\n"
            "📞 Админ: @evelineee_00"
        )
        back_text = "🔙 Назад"
    else:
        text = (
            "ℹ️ **Help Center**\n\n"
            "If you have any issues, please contact the admin:\n"
            "📞 Admin: @evelineee_00"
        )
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="Markdown")

# Admin panel
@dp.callback_query(F.data.startswith("admin_"))
async def admin_panel(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return await callback.answer("Siz admin emassiz!", show_alert=True)

    lang = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_stats_{lang}")],
        [InlineKeyboardButton(text="📢 Xabar yuborish", callback_data=f"admin_broadcast_{lang}")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text("⚙️ <b>Admin Panel</b>\nKerakli bo'limni tanlang:", reply_markup=kb, parse_mode="HTML")

@dp.callback_query(F.data.startswith("admin_stats_"))
async def admin_stats(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
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

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_{lang}")]])
    await callback.message.edit_text(
        f"📊 <b>Statistika:</b>\n\n"
        f"• Jami buyurtmalar: {total_orders}\n"
        f"• Muvaffaqiyatli savdo: {total_sum:,.0f} so'm",
        reply_markup=kb,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("admin_broadcast_"))
async def admin_broadcast(callback: types.CallbackQuery):
    await callback.answer("Broadcast xizmati tez orada qo'shiladi!", show_alert=True)

# Ichki bo'limlardan to'g'ridan-to'g'ri til tanlash menyusiga emas, balki o'sha tilning asosiy menyusiga qaytish
@dp.callback_query(F.data.startswith("back_to_main_"))
async def back_to_main(callback: types.CallbackQuery):
    lang = callback.data.split("_")[3]
    text, kb = await get_main_menu(callback.from_user.id, lang)
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

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
    
