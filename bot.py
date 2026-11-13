import asyncio
import logging
import sqlite3
from os import getenv
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo, FSInputFile

import config

# ===========================================================================
# 1-QISM: LOGGING VA ASOSIY SOZLAMALAR
# ===========================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# ===========================================================================
# 2-QISM: BAZANI INITSIALIZATSIYA QILISH VA KENGAYTIRISH
# ===========================================================================
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
        logger.error(f"Foydalanuvchini ro'yxatdan o'tkazishda xatolik: {e}")
    finally:
        conn.close()

def get_user_balance(user_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

# ===========================================================================
# 3-QISM: START BUYRUQ VA TIL TANLASH
# ===========================================================================
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
    
    welcome_text = (
        "🌐 Iltimos, tilni tanlang / Пожалуйста, выберите язык / Please select a language:\n\n"
        "✨ <i>Ultimate Donat Bot v3.0</i> ga xush kelibsiz!"
    )
    
    await message.answer(welcome_text, reply_markup=kb, parse_mode="HTML")

# ===========================================================================
# 4-QISM: ASOSIY MENYU GENERATORI
# ===========================================================================
async def get_main_menu(user_id: int, lang: str):
    balance = get_user_balance(user_id)
    
    if lang == "uz":
        text = (
            f"👋 Assalomu alaykum!\n\n"
            f"💰 **Sizning balansingiz:** <code>{balance:,} so'm</code>\n\n"
            "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar, Telegram xizmatlari va NFT'larni eng qulay narxlarda xarid qiling.\n\n"
            "📦 Buyurtma berish uchun pastdagi Mini App do'konidan foydalaning:"
        )
        btn_shop = "🛒 Do'konni ochish (Mini App)"
        btn_orders = "📦 Buyurtmalarim"
        btn_topup = "💳 Balansni to'ldirish"
        btn_help = "ℹ️ Yordam"
        btn_prices = "💰 Narxlar jadvali"
        btn_admin = "⚙️ Admin Panel"
    elif lang == "ru":
        text = (
            f"👋 Здравствуйте!\n\n"
            f"💰 **Ваш баланс:** <code>{balance:,} сум</code>\n\n"
            "🎮 Добро пожаловать в <b>Ultimate Donat Bot</b>. Покупайте игры, Telegram-услуги и NFT по выгодным ценам.\n\n"
            "📦 Используйте магазин Mini App ниже для заказа:"
        )
        btn_shop = "🛒 Открыть магазин (Mini App)"
        btn_orders = "📦 Мои заказы"
        btn_topup = "💳 Пополнить баланс"
        btn_help = "ℹ️ Помощь"
        btn_prices = "💰 Таблица цен"
        btn_admin = "⚙️ Админ панель"
    else:
        text = (
            f"👋 Hello!\n\n"
            f"💰 **Your Balance:** <code>{balance:,} UZS</code>\n\n"
            "🎮 Welcome to <b>Ultimate Donat Bot</b>. Buy games, Telegram services, and NFTs at the best prices.\n\n"
            "📦 Use the Mini App store below to place an order:"
        )
        btn_shop = "🛒 Open Shop (Mini App)"
        btn_orders = "📦 My Orders"
        btn_topup = "💳 Top up balance"
        btn_help = "ℹ️ Help"
        btn_prices = "💰 Price List"
        btn_admin = "⚙️ Admin Panel"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=btn_shop, web_app=WebAppInfo(url="https://donat-bot-cl4x.onrender.com"))],
        [
            InlineKeyboardButton(text=btn_orders, callback_data=f"orders_{lang}"),
            InlineKeyboardButton(text=btn_topup, callback_data=f"topup_{lang}")
        ],
        [
            InlineKeyboardButton(text=btn_prices, callback_data=f"prices_{lang}"),
            InlineKeyboardButton(text=btn_help, callback_data=f"help_{lang}")
        ]
    ])
    
    if user_id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text=btn_admin, callback_data=f"admin_{lang}")])

    return text, kb

# ===========================================================================
# 5-QISM: TIL VA ASOSIY MENYU HANDLERLARI
# ===========================================================================
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

# ===========================================================================
# 6-QISM: BALANSNI TO'LDIRISH BO'LIMI
# ===========================================================================
@dp.callback_query(F.data.startswith("topup_"))
async def topup_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    if lang == "uz":
        text = (
            "💳 **Balansni to'ldirish tartibi:**\n\n"
            f"1. Quyidagi karta raqamiga kerakli summani o'tkazing:\n"
            f"<code>{config.CARD_NUMBER}</code>\n"
            f"Karta egasi: <b>{config.CARD_HOLDER}</b>\n\n"
            "2. Pulni o'tkazgach, chek rasmini shu botga yuboring.\n"
            "3. Admin tekshirgach, balansingiz avtomatik qo'shiladi!"
        )
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = (
            "💳 **Пополнение баланса:**\n\n"
            f"1. Переведите нужную сумму на карту:\n"
            f"<code>{config.CARD_NUMBER}</code>\n"
            f"Владелец: <b>{config.CARD_HOLDER}</b>\n\n"
            "2. После отправки отправьте скриншот чека в этот бот.\n"
            "3. После проверки администратором баланс обновится!"
        )
        back_text = "🔙 Назад"
    else:
        text = (
            "💳 **Top up balance:**\n\n"
            f"1. Transfer the required amount to the card:\n"
            f"<code>{config.CARD_NUMBER}</code>\n"
            f"Holder: <b>{config.CARD_HOLDER}</b>\n\n"
            "2. Send the payment receipt screenshot to this bot.\n"
            "3. Admin will verify and credit your balance!"
        )
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ===========================================================================
# 7-QISM: SCREENSHOT / CHEKNI QABUL QILISH
# ===========================================================================
@dp.message(F.photo)
async def handle_receipt_photo(message: types.Message):
    user = message.from_user
    photo_id = message.photo[-1].file_id
    
    caption = (
        f"📥 **Yangi to'lov cheki keldi!**\n\n"
        f"• Foydalanuvchi: <a href='tg://user?id={user.id}'>{user.full_name}</a>\n"
        f"• Username: @{user.username or 'yoq'}\n"
        f"• ID: <code>{user.id}</code>"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{user.id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user.id}")
        ]
    ])
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"Adminga chek yuborishda xatolik: {e}")
            
    await message.answer("✅ To'lov chekingiz adminga yuborildi! Tez orada ko'rib chiqiladi.")

# ===========================================================================
# 8-QISM: ADMIN TASDIQLASH / RAD ETISH HANDLERLARI
# ===========================================================================
@dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
async def process_payment_decision(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Huquqingiz yo'q!", show_alert=True)
        return
        
    action, target_user_id = callback.data.split("_")
    target_user_id = int(target_user_id)
    
    if action == "approve":
        await bot.send_message(target_user_id, "✅ Sizning to'lovingiz admin tomonidan tasdiqlandi va balansingizga qo'shildi!")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n<b>STATUS: TASDIQLANDI ✅</b>", parse_mode="HTML")
    else:
        await bot.send_message(target_user_id, "❌ Siz yuborgan to'lov cheki rad etildi. Iltimos, admin bilan bog'laning: @evelineee_00")
        await callback.message.edit_caption(caption=callback.message.caption + "\n\n<b>STATUS: RAD ETILDI ❌</b>", parse_mode="HTML")
        
    await callback.answer("Amal bajarildi!")

# ===========================================================================
# 9-QISM: BUYURTMALARIM BO'LIMI
# ===========================================================================
@dp.callback_query(F.data.startswith("orders_"))
async def my_orders_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id, item_name, amount, status FROM orders WHERE user_id = ?", (callback.from_user.id,))
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
                text += f"• ID: <code>{o[0]}</code> | {o[1]} | {o[2]} so'm | Holati: <b>{o[3]}</b>\n"
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        if not orders:
            text = "📦 У вас пока нет активных заказов."
        else:
            text = "📦 **Ваши заказы:**\n\n"
            for o in orders:
                text += f"• ID: <code>{o[0]}</code> | {o[1]} | {o[2]} сум | Статус: <b>{o[3]}</b>\n"
        back_text = "🔙 Назад"
    else:
        if not orders:
            text = "📦 You have no active orders yet."
        else:
            text = "📦 **Your Orders:**\n\n"
            for o in orders:
                text += f"• ID: <code>{o[0]}</code> | {o[1]} | {o[2]} UZS | Status: <b>{o[3]}</b>\n"
        back_text = "🔙 Back"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=back_text, callback_data=f"back_to_main_{lang}")]
    ])
    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()

# ===========================================================================
# 10-QISM: YORDAM MARKAZI
# ===========================================================================
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

# ===========================================================================
# 11-QISM: NARXLAR JADVALI
# ===========================================================================
@dp.callback_query(F.data.startswith("prices_"))
async def prices_handler(callback: types.CallbackQuery):
    lang = callback.data.split("_")[1]
    
    if lang == "uz":
        text = (
            "💰 **Xizmatlar va O'yinlar Narxnomasi:**\n\n"
            "• Telegram Premium (1 oy) — 40,000 so'm\n"
            "• Telegram Premium (1 yil) — 300,000 so'm\n"
            "• UC (PUBG Mobile) — Kelishilgan holda\n"
            "• Stars (Telegram yulduzlari) — Arzon narxlarda\n\n"
            "Batafsil ma'lumot Mini App do'konida joylashgan!"
        )
        back_text = "🔙 Orqaga"
    elif lang == "ru":
        text = (
            "💰 **Прайс-лист услуг и игр:**\n\n"
            "• Telegram Premium (1 месяц) — 40,000 сум\n"
            "• Telegram Premium (1 год) — 300,000 сум\n"
            "• UC (PUBG Mobile) — По договоренности\n"
            "• Stars (Telegram звезды) — По доступным ценам\n\n"
            "Подробная информация в магазине Mini App!"
        )
        back_text = "🔙 Назад"
    else:
        text = (
            "💰 **Services & Games Price List:**\n\n"
            "• Telegram Premium (1 month) — 40,000 UZS\n"
            "• Telegram Premium (1 year) — 300,000 UZS\n"
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

# ===========================================================================
# 12-QISM: ADMIN PANEL VA STATISTIKA
# ===========================================================================
@dp.callback_query(F.data.startswith("admin_"))
async def admin_panel_handler(callback: types.CallbackQuery):
    if callback.from_user.id not in config.ADMIN_IDS:
        await callback.answer("Sizda bu bo'limga kirish huquqi yo'q!", show_alert=True)
        return

    lang = callback.data.split("_")[1]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Statistika", callback_data=f"admin_stats_{lang}")],
        [InlineKeyboardButton(text="👥 Foydalanuvchilar soni", callback_data=f"admin_users_{lang}")],
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
        cursor.execute("SELECT SUM(amount) FROM orders")
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
        f"• Jami buyurtmalar: <b>{total_orders} ta</b>\n"
        f"• Jami summa: <b>{total_sum:,.0f} so'm</b>\n"
        f"• Faol karta: <code>{config.CARD_NUMBER}</code>",
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
        f"👥 <b>Foydalanuvchilar:</b>\n\n"
        f"• Ro'yxatdan o'tganlar: <b>{total_users} ta</b>",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await callback.answer()

# ===========================================================================
# 13-QISM: ASOSIY MENYUGA QAYTISH
# ===========================================================================
@dp.callback_query(F.data.startswith("back_to_main_"))
async def back_to_main_menu(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    lang = parts[3] if len(parts) > 3 else "uz"
    
    text, kb = await get_main_menu(callback.from_user.id, lang)
    try:
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        logger.error(f"Asosiy menyuga qaytishda xatolik: {e}")
        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
    await callback.answer()
  # ===========================================================================
# 14-QISM: WEB-SERVER VA ISHGA TUSHIRISH (MAIN)
# ===========================================================================
async def handle_ping(request):
    return web.Response(text="Ultimate Donat Bot serveri ishlamoqda!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logger.info(f"Aiohttp web server {port}-portda ishga tushdi.")

async def main():
    init_db()
    asyncio.create_task(start_web_server())
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("Bot polling rejimi boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi!")
    
