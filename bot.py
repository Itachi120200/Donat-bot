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

# Logging sozlamalari
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# Ma'lumotlar bazasi bilan ishlash funksiyasi
def get_db():
    return sqlite3.connect('bot_database.db')

# Foydalanuvchini bazaga qo'shish (agar bo'lmasa)
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
        logger.error(f"Foydalanuvchini ro'yxatdan o'tkazishda xatolik: {e}")
    finally:
        conn.close()

# ---------------------------------------------------------------------------
# START BUYrug'i va Til tanlash
# ---------------------------------------------------------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Foydalanuvchini avtomatik bazaga yozib qoldiramiz
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
    
    welcome_text = (
        "🌐 Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:\n\n"
        "✨ <i>Ultimate Donat Bot v2.5</i> ga xush kelibsiz!"
    )
    
    await message.answer(welcome_text, reply_markup=kb, parse_mode="HTML")


# ---------------------------------------------------------------------------
# ASOSIY MENYU GENERATORI (Yordamchi funksiya)
# ---------------------------------------------------------------------------
async def get_main_menu(user_id: int, lang: str):
    if lang == "uz":
        text = (
            f"👋 Assalomu alaykum!\n\n"
            "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar, Telegram xizmatlari va NFT'larni eng qulay narxlarda xarid qiling.\n\n"
            "📦 Buyurtma berish yoki balansni to'ldirish uchun pastdagi Mini App do'konidan foydalaning:"
        )
        btn_shop = "🛒 Do'konni ochish (Mini App)"
        btn_orders = "📦 Buyurtmalarim"
        btn_help = "ℹ️ Yordam"
        btn_prices = "💰 Narxlar jadvali"
        btn_admin = "⚙️ Admin Panel"
    elif lang == "ru":
        text = (
            f"👋 Здравствуйте!\n\n"
            "🎮 Добро пожаловать в <b>Ultimate Donat Bot</b>. Покупайте игры, Telegram-услуги и NFT по выгодным ценам.\n\n"
            "📦 Используйте магазин Mini App ниже для заказа:"
        )
        btn_shop = "🛒 Открыть магазин (Mini App)"
        btn_orders = "📦 Мои заказы"
        btn_help = "ℹ️ Помощь"
        btn_prices = "💰 Таблица цен"
        btn_admin = "⚙️ Админ панель"
    else:
        text = (
            f"👋 Hello!\n\n"
            "🎮 Welcome to <b>Ultimate Donat Bot</b>. Buy games, Telegram services, and NFTs at the best prices.\n\n"
            "📦 Use the Mini App store below to place an order:"
        )
        btn_shop = "🛒 Open Shop (Mini App)"
        btn_orders = "📦 My Orders"
        btn_help = "ℹ️ Help"
        btn_prices = "💰 Price List"
        btn_admin = "⚙️ Admin Panel"

    # Render manzili to'g'ridan-to'g'ri Mini App'ga ulandi
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_shop, web_app=WebAppInfo(url="https://donat-bot-cl4x.onrender.com"))],
        [
            InlineKeyboardButton(text=btn_orders, callback_data=f"orders_{lang}"),
            InlineKeyboardButton(text=btn_help, callback_data=f"help_{lang}")
        ],
        [
            InlineKeyboardButton(text=btn_prices, callback_data=f"prices_{lang}")
        ]
    ])
    
    # Agar foydalanuvchi admin bo'lsa, admin panel tugmasini qo'shamiz
    if user_id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_admin, callback_data=f"admin_{lang}")])

    return text, kb


# ---------------------------------------------------------------------------
# TIL TANLANDEGAN PAYTDagi HANDLER
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("lang_"))
async def set_language(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    text, kb = await get_main_menu(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Tilni o'rnatishda xatolik: {e}")
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------------------------------------------------------------------------
# BUYURTMALARIM BO'LIMI
# ---------------------------------------------------------------------------
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
    finally:
        conn.close()

    if lang == "uz":
        if not orders:
            text = "📦 Sizda hozircha faol buyurtmalar mavjud emas."
        else:
            text = "📦 **Sizning barcha buyurtmalaringiz:**\n\n"
            for o in orders:
                text += f"• ID: <code>{o[0]}</code> | Summa: {o[1]} so'm | Holati: <b>{o[2]}</b>\n"
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        if not orders:
            text = "📦 У вас пока нет активных заказов."
        else:
            text = "📦 **Ваши заказы:**\n\n"
            for o in orders:
                text += f"• ID: <code>{o[0]}</code> | Сумма: {o[1]} сум | Статус: <b>{o[2]}</b>\n"
        back_text = "🔙 Назад"
    else:
        if not orders:
            text = "📦 You have no active orders yet."
        else:
            text = "📦 **Your Orders:**\n\n"
            for o in orders:
                text += f"• ID: <code>{o[0]}</code> | Amount: {o[1]} UZS | Status: <b>{o[2]}</b>\n"
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------------------------------------------------------------------------
# YORDAM MARKAZI BO'LIMI
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("help_"))
async def help_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    if lang == "uz":
        text = (
            "ℹ️ **Yordam va Qo'llab-quvvatlash markazi**\n\n"
            "To'lov qilishda muammo yuzaga kelsa yoki buyurtmangiz vaqtida kelmasa, "
            "darhol rasmiy adminimizga murojaat qiling:\n\n"
            "📞 **Admin bilan bog'lanish:** @evelineee_00\n"
            "⏰ Ish vaqti: 24/7 rejimida."
        )
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = (
            "ℹ️ **Центр помощи и поддержки**\n\n"
            "Если у вас возникли проблемы с оплатой или заказ задерживается, "
            "немедленно обратитесь к нашему администратору:\n\n"
            "📞 **Связь с админом:** @evelineee_00\n"
            "⏰ Режим работы: 24/7."
        )
        back_text = "🔙 Назад"
    else:
        text = (
            "ℹ️ **Help & Support Center**\n\n"
            "If you experience any issues with payments or your order is delayed, "
            "please contact our administrator immediately:\n\n"
            "📞 **Contact Admin:** @evelineee_00\n"
            "⏰ Working hours: 24/7."
        )
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------------------------------------------------------------------------
# NARXLAR JADVALI QO'SHIMCHA BO'LIMI
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("prices_"))
async def prices_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    if lang == "uz":
        text = (
            "💰 **Xizmatlar va O'yinlar Narxnomasi:**\n\n"
            "• Telegram Premium (1 oy) — 25,000 so'm\n"
            "• Telegram Premium (1 yil) — 190,000 so'm\n"
            "• UC (PUBG Mobile) — Kelishilgan holda\n"
            "• Stars (Telegram yulduzlari) — Arzon narxlarda\n\n"
            "Batafsil ma'lumot Mini App do'konida joylashgan!"
        )
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = (
            "💰 **Прайс-лист услуг и игр:**\n\n"
            "• Telegram Premium (1 месяц) — 25,000 сум\n"
            "• Telegram Premium (1 год) — 190,000 сум\n"
            "• UC (PUBG Mobile) — По договоренности\n"
            "• Stars (Telegram звезды) — По доступным ценам\n\n"
            "Подробная информация в магазине Mini App!"
        )
        back_text = "🔙 Назад"
    else:
        text = (
            "💰 **Services & Games Price List:**\n\n"
            "• Telegram Premium (1 month) — 25,000 UZS\n"
            "• Telegram Premium (1 year) — 190,000 UZS\n"
            "• UC (PUBG Mobile) — Negotiable\n"
            "• Stars (Telegram stars) — Best rates\n\n"
            "More details available in the Mini App store!"
        )
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()


# ---------------------------------------------------------------------------
# ADMIN PANEL BO'LIMI
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("admin_"))
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Sizda bu bo'limga kirish huquqi yo'q!", show_alert=True)
        return

    lang = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_stats_{lang}")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar soni", callback_data=f"admin_users_{lang}")],
        [InlineKeyboardButton(text="📢 Broadcast (Xabar tarqatish)", callback_data=f"admin_broadcast_{lang}")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text("⚙️ <b>Admin Boshqaruv Paneli</b>\nKerakli amalni tanlang:", reply_markup=kb, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_stats_"))
async def admin_stats_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
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
    finally:
        conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_{lang}")]
    ])
    await callback.message.edit_text(
        f"📊 <b>Bot Statistikasi:</b>\n\n"
        f"• Jami buyurtmalar soni: <b>{total_orders} ta</b>\n"
        f"• Muvaffaqiyatli savdo summasi: <b>{total_sum:,.0f} so'm</b>\n"
        f"• Faol to'lov kartasi: <code>{config.CARD_NUMBER}</code>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_users_"))
async def admin_users_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    lang = callback.data.split("_")[1]
    
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM users")
        total_users = cursor.fetchone()[0]
    except sqlite3.OperationalError:
        total_users = 1
    finally:
        conn.close()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"admin_{lang}")]
    ])
    await callback.message.edit_text(
        f"👥 <b>Foydalanuvchilar statistikasi:</b>\n\n"
        f"• Botdan ro'yxatdan o'tganlar: <b>{total_users} ta</b> foydalanuvchi.",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_broadcast_"))
async def admin_broadcast_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        return
    await callback.answer("📢 Broadcast funksiyasi keyingi yangilanishda qo'shiladi!", show_alert=True)


# ---------------------------------------------------------------------------
# ASOSIY MENYUGA QAYTISH HANDLERI
# ---------------------------------------------------------------------------
@dp.callback_query(F.data.startswith("back_to_main_"))
async def back_to_main_menu(callback: types.CallbackQuery):
    # Callback formatidan tilni ajratib olamiz (back_to_main_uz -> uz)
    parts = callback.data.split("_")
    lang = parts[3] if len(parts) > 3 else "uz"
    
    text, kb = await get_main_menu(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Asosiy menyuga qaytishda xatolik: {e}")
    await callback.answer()


# ---------------------------------------------------------------------------
# RENDER UCHUN AIOHTTP WEB-SERVER QISMI
# ---------------------------------------------------------------------------
async def handle_ping(request):
    return web.Response(text="Ultimate Donat Bot serveri faol ishlamoqda!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Veb-server {port}-portda muvaffaqiyatli ishga tushdi.")


# ---------------------------------------------------------------------------
# ASOSIY ISHGA TUSHIRISH FUNKSIYASI
# ---------------------------------------------------------------------------
async def main():
    # Ma'lumotlar bazasini initsializatsiya qilish
    init_db()
    logger.info("Ma'lumotlar bazasi ulandi va tekshirildi.")
    print("Bot muvaffaqiyatli ishga tushdi...")
    
    # Render veb-serveri va Telegram bot polling jarayonini birga parallel ishga tushiramiz
    await asyncio.gather(
        web_server(),
        dp.start_polling(bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
