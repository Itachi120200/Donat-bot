import asyncio
import logging
import sqlite3
from os import getenv
from aiohttp import web
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

def init_db():
    conn = sqlite3.connect('bot_database.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            balance INTEGER DEFAULT 0,
            joined_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            item_name TEXT,
            amount INTEGER,
            status TEXT DEFAULT 'Kutilmoqda',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS promos (
            code TEXT PRIMARY KEY,
            discount INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def get_db():
    return sqlite3.connect('bot_database.db')

def register_user(user_id: int, username: str, full_name: str):
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id, username, full_name) VALUES (?, ?, ?)",
            (user_id, username, full_name)
        )
        conn.commit()
    except Exception as e:
        logger.error(f"Xatolik: {e}")
    finally:
        conn.close()

def get_user_balance(user_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def update_user_balance(user_id: int, amount: int):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()
    conn.close()

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    register_user(
        message.from_user.id,
        message.from_user.username or "",
        message.from_user.full_name or "K"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="lang_uz"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru"),
            InlineKeyboardButton(text="🇬🇧 English", callback_data="lang_en")
        ]
    ])
    await message.answer(
        "🌐 Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:\n\n✨ <i>Ultimate Donat Bot v3.0</i> ga xush kelibsiz!",
        reply_markup=kb, parse_mode="HTML"
    )

async def get_main_menu(user_id: int, lang: str):
    balance = get_user_balance(user_id)
    if lang == "uz":
        text = (
            f"👋 Assalomu alaykum!\n\n"
            f"💰 **Sizning balansingiz:** <code>{balance:,} so'm</code>\n\n"
            "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar va xizmatlarni xarid qiling.\n\n"
            "📦 Buyurtma berish uchun pastdagi Mini App do'konidan foydalaning:"
        )
        btn_shop, btn_orders, btn_topup, btn_help, btn_prices, btn_admin = (
            "🛒 Do'konni ochish (Mini App)", "📦 Buyurtmalarim", "💳 Balansni to'ldirish", "ℹ️ Yordam", "💰 Narxlar jadvali", "⚙️ Admin Panel"
        )
    elif lang == "ru":
        text = (
            f"👋 Здравствуйте!\n\n"
            f"💰 **Ваш баланс:** <code>{balance:,} сум</code>\n\n"
            "🎮 Добро пожаловать в <b>Ultimate Donat Bot</b>.\n\n"
            "📦 Используйте магазин Mini App ниже для заказа:"
        )
        btn_shop, btn_orders, btn_topup, btn_help, btn_prices, btn_admin = (
            "🛒 Открыть магазин (Mini App)", "📦 Мои заказы", "💳 Пополнить баланс", "ℹ️ Помощь", "💰 Таблица цен", "⚙️ Админ панель"
        )
    else:
        text = (
            f"👋 Hello!\n\n"
            f"💰 **Your Balance:** <code>{balance:,} UZS</code>\n\n"
            "🎮 Welcome to <b>Ultimate Donat Bot</b>.\n\n"
            "📦 Use the Mini App store below to place an order:"
        )
        btn_shop, btn_orders, btn_topup, btn_help, btn_prices, btn_admin = (
            "🛒 Open Shop (Mini App)", "📦 My Orders", "💳 Top up balance", "ℹ️ Help", "💰 Price List", "⚙️ Admin Panel"
        )

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_shop, web_app=WebAppInfo(url="https://donat-bot-cl4x.onrender.com"))],
        [InlineKeyboardButton(text=btn_orders, callback_data=f"orders_{lang}"), InlineKeyboardButton(text=btn_topup, callback_data=f"topup_{lang}")],
        [InlineKeyboardButton(text=btn_prices, callback_data=f"prices_{lang}"), InlineKeyboardButton(text=btn_help, callback_data=f"help_{lang}")]
    ])
    if user_id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_admin, callback_data=f"admin_{lang}")])
    return text, kb

@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    text, kb = await get_main_menu(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("topup_"))
async def topup_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    if lang == "uz":
        text = f"💳 **Balansni to'ldirish:**\n\n1. Karta: <code>{config.CARD_NUMBER}</code>\nEgasi: <b>{config.CARD_HOLDER}</b>\n\n2. Chek rasmini yuboring."
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = f"💳 **Пополнение баланса:**\n\n1. Карта: <code>{config.CARD_NUMBER}</code>\nВладелец: <b>{config.CARD_HOLDER}</b>\n\n2. Отправьте скрин чека."
        back_text = "🔙 Назад"
    else:
        text = f"💳 **Top up:**\n\n1. Card: <code>{config.CARD_NUMBER}</code>\nHolder: <b>{config.CARD_HOLDER}</b>\n\n2. Send receipt."
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.message(F.photo)
async def handle_receipt_photo(message: types.Message):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    caption = f"📥 **Yangi chek!**\n\n• Kimdan: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n• ID: <code>{user.id}</code>"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash (+10,000)", callback_data=f"approve_{user.id}_10000"), InlineKeyboardButton(text="(+50,000)", callback_data=f"approve_{user.id}_50000")],
        [InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user.id}")]
    ])
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
        except Exception:
            pass
    await message.answer("✅ Chek adminga yuborildi!")

@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def process_payment_decision(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Huquqingiz yo'q!", show_alert=True)
        return
    parts = callback.data.split("_")
    action, target_user_id = parts[0], int(parts[1])
    if action == "approve":
        amount = int(parts[2]) if len(parts) > 2 else 10000
        update_user_balance(target_user_id, amount)
        await bot.send_message(target_user_id, f"✅ To'lovingiz tasdiqlandi! Balansingizga <b>{amount:,} so'm</b> qo'shildi.", parse_mode="HTML")
        await callback.message.edit_caption(caption=callback.message.caption + f"\n\n<b>STATUS: TASDIQLANDI (+{amount:,} so'm) ✅</b>", parse_mode="HTML")
    else:
        await bot.send_message(target_user_id, "❌ Chekingiz rad etildi.")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n<b>STATUS: RAD ETILDI ❌</b>", parse_mode="HTML")
    await callback.answer("Bajarildi!")

@dp.callback_query(F.data.startswith("orders_"))
async def my_orders_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, item_name, amount, status FROM orders WHERE user_id = ?", (callback.from_user.id,))
        orders = cursor.fetchall()
    except Exception:
        orders = []
    finally:
        conn.close()
    text = "📦 **Buyurtmalaringiz:**\n\n" if orders else "📦 Buyurtmalar yo'q."
    for o in orders:
        text += f"• ID: <code>{o[0]}</code> | {o[1]} | {o[2]} so'm | <b>{o[3]}</b>\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("help_"))
async def help_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text("ℹ️ **Yordam markazi:**\n📞 @evelineee_00", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("prices_"))
async def prices_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"back_to_main_{lang}")]])
    await callback.message.edit_text("💰 **Narxlar:**\n• Telegram Premium (1 oy) — 40,000 so'm", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_"))
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Huquq yo'q!", show_alert=True)
        return
    data_parts = callback.data.split("_")
    lang = data_parts[-1]
    if callback.data.startswith("admin_stats_"):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM orders")
            total_orders = cursor.fetchone()[0]
            cursor.execute("SELECT SUM(amount) FROM orders")
            total_sum = cursor.fetchone()[0] or 0
            cursor.execute("SELECT SUM(balance) FROM users")
            total_balance = cursor.fetchone()[0] or 0
        except Exception:
            total_orders, total_sum, total_balance = 0, 0, 0
        finally:
            conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_{lang}")]])
        await callback.message.edit_text(
            f"📊 **Statistika:**\n\n• Buyurtmalar: <b>{total_orders} ta</b>\n• Jami summa: <b>{total_sum:,.0f} so'm</b>\n• Balanslar yig'indisi: <b>{total_balance:,.0f} so'm</b>",
            reply_markup=kb, parse_mode="HTML"
        )
        await callback.answer()
        return
    if callback.data.startswith("admin_users_"):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM users")
            total_users = cursor.fetchone()[0]
        except Exception:
            total_users = 1
        finally:
            conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_{lang}")]])
        await callback.message.edit_text(f"👥 **Foydalanuvchilar:** <b>{total_users} ta</b>", reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_stats_{lang}")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data=f"admin_users_{lang}")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text("⚙️ <b>Admin Panel</b>", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("back_to_main_"))
async def back_to_main_menu(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    lang = parts[3] if len(parts) > 3 else "uz"
    text, kb = await get_main_menu(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

async def handle_ping(request):
    try:
        return aiohttp.web.FileResponse('index.html')
    except Exception:
        return web.Response(text="Do'kon sahifasi yuklanmoqda...", content_type='text/html')

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_get("/shop", handle_ping)
    
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Web server {port}-portda ishga tushdi.")

async def main():
    init_db()
    asyncio.create_task(start_web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
    
