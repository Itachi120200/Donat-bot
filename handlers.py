import sqlite3
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo

import config

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
        pass
    finally:
        conn.close()

def get_user_balance(user_id: int) -> int:
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    conn.close()
    return res[0] if res else 0

def get_main_menu(user_id: int):
    balance = get_user_balance(user_id)
    text = (
        f"👋 Assalomu alaykum!\n\n"
        f"💰 <b>Shaxsiy balansingiz:</b> <code>{balance:,} so'm</code>\n\n"
        "🎮 <b>Ultimate Donat Bot</b>ga xush kelibsiz. O'yinlar va xizmatlarni qulay narxlarda xarid qiling.\n\n"
        "📦 Buyurtma berish uchun Mini App do'konidan foydalaning:"
    )
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛒 Do'konni ochish (Mini App)", web_app=WebAppInfo(url="https://donat-bot-cl4x.onrender.com"))],
        [
            InlineKeyboardButton(text="📦 Buyurtmalarim", callback_data="menu_orders"),
            InlineKeyboardButton(text="💳 Balansni to'ldirish", callback_data="menu_topup")
        ],
        [
            InlineKeyboardButton(text="🎁 Promo-kod", callback_data="menu_promo"),
            InlineKeyboardButton(text="💰 Narxlar jadvali", callback_data="menu_prices")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Yordam markazi", callback_data="menu_help")
        ]
    ])
    
    if user_id in config.ADMIN_IDS:
        kb.inline_keyboard.append([InlineKeyboardButton(text="⚙️ Admin Paneli", callback_data="menu_admin")])

    return text, kb

def register_handlers(dp: Dispatcher, bot: Bot):

    @dp.message(Command("start"))
    async def cmd_start(message: types.Message):
        register_user(message.from_user.id, message.from_user.username or "", message.from_user.full_name or "K")
        text, kb = get_main_menu(message.from_user.id)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")

    @dp.callback_query(F.data == "back_to_main")
    async def back_to_main(callback: types.CallbackQuery):
        text, kb = get_main_menu(callback.from_user.id)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "menu_topup")
    async def topup_handler(callback: types.CallbackQuery):
        text = (
            "💳 <b>Balansni to'ldirish:</b>\n\n"
            f"1. Karta raqamiga o'tkazing:\n<code>{config.CARD_NUMBER}</code>\n"
            f"Egasi: <b>{config.CARD_HOLDER}</b>\n\n"
            "2. Chek rasmini shu botga yuboring."
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.message(F.photo)
    async def handle_receipt_photo(message: types.Message):
        user = message.from_user
        photo_id = message.photo[-1].file_id
        caption = f"📥 <b>Yangi chek!</b>\n• Kimdan: {user.full_name} (<code>{user.id}</code>)"
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"approve_{user.id}"),
                InlineKeyboardButton(text="❌ Rad etish", callback_data=f"reject_{user.id}")
            ]
        ])
        for admin_id in config.ADMIN_IDS:
            try:
                await bot.send_photo(chat_id=admin_id, photo=photo_id, caption=caption, reply_markup=kb, parse_mode="HTML")
            except:
                pass
        await message.answer("✅ Chekingiz adminga yuborildi!")

    @dp.callback_query(F.data.startswith("approve_") | F.data.startswith("reject_"))
    async def payment_decision(callback: types.CallbackQuery):
        if callback.from_user.id not in config.ADMIN_IDS:
            return
        action, target_id = callback.data.split("_")
        target_id = int(target_id)
        if action == "approve":
            await bot.send_message(target_id, "✅ To'lovingiz tasdiqlandi!")
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n<b>TASDIQLANDI ✅</b>", parse_mode="HTML")
        else:
            await bot.send_message(target_id, "❌ To'lovingiz rad etildi.")
            await callback.message.edit_caption(caption=callback.message.caption + "\n\n<b>RAD ETILDI ❌</b>", parse_mode="HTML")
        await callback.answer("Bajarildi!")

    @dp.callback_query(F.data == "menu_promo")
    async def promo_menu(callback: types.CallbackQuery):
        text = "🎁 **Promo-kod bo'limi**\n\nFaollashtirish uchun yuboring:\n`/promo KOD`"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.message(Command("promo"))
    async def apply_promo(message: types.Message):
        args = message.text.split()
        if len(args) < 2:
            await message.answer("⚠️ Masalan: `/promo ULTIMATE`", parse_mode="HTML")
            return
        code = args[1].strip().upper()
        user_id = message.from_user.id
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT discount FROM promos WHERE code = ?", (code,))
        promo = cursor.fetchone()
        if not promo:
            conn.close()
            await message.answer("❌ Bunday promo-kod yo'q.")
            return
        discount = promo[0]
        cursor.execute("SELECT * FROM used_promos WHERE user_id = ? AND code = ?", (user_id, code))
        if cursor.fetchone():
            conn.close()
            await message.answer("⚠️ Bu kodni oldin ishlatgansiz!")
            return
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (discount, user_id))
        cursor.execute("INSERT INTO used_promos (user_id, code) VALUES (?, ?)", (user_id, code))
        conn.commit()
        conn.close()
        await message.answer(f"🎉 Tabriklaymiz! Balansingizga <b>{discount:,} so'm</b> qo'shildi!", parse_mode="HTML")

    @dp.callback_query(F.data == "menu_orders")
    async def orders_handler(callback: types.CallbackQuery):
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT id, item_name, amount, status FROM orders WHERE user_id = ?", (callback.from_user.id,))
            orders = cursor.fetchall()
        except:
            orders = []
        finally:
            conn.close()
        text = "📦 **Sizning buyurtmalaringiz:**\n\n" if orders else "📦 Faol buyurtmalar yo'q."
        for o in orders:
            text += f"• ID: {o[0]} | {o[1]} — {o[2]} so'm ({o[3]})\n"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "menu_prices")
    async def prices_handler(callback: types.CallbackQuery):
        text = "💰 **Narxlar:**\n• Telegram Premium (1 oy) — 40,000 so'm\n• Telegram Premium (1 yil) — 300,000 so'm"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "menu_help")
    async def help_handler(callback: types.CallbackQuery):
        text = "ℹ️ **Yordam:**\nAdmin: @evelineee_00"
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "menu_admin")
    async def admin_panel(callback: types.CallbackQuery):
        if callback.from_user.id not in config.ADMIN_IDS:
            await callback.answer("Huquq yo'q!", show_alert=True)
            return
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📊 Statistika", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_main")]
        ])
        await callback.message.edit_text("⚙️ **Admin Panel**", reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.callback_query(F.data == "admin_stats")
    async def admin_stats(callback: types.CallbackQuery):
        if callback.from_user.id not in config.ADMIN_IDS:
            return
        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), SUM(amount) FROM orders")
            res = cursor.fetchone()
            cnt, sm = res[0] or 0, res[1] or 0
        except:
            cnt, sm = 0, 0
        finally:
            conn.close()
        kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Orqaga", callback_data="menu_admin")]])
        await callback.message.edit_text(f"📊 Jami buyurtmalar: {cnt} ta\nSumma: {sm:,} so'm", reply_markup=kb, parse_mode="HTML")
        await callback.answer()

    @dp.message(Command("addpromo"))
    async def add_promo(message: types.Message):
        if message.from_user.id not in config.ADMIN_IDS:
            return
        args = message.text.split()
        if len(args) < 3:
            await message.answer("Format: `/addpromo KOD SUMMA`", parse_mode="HTML")
            return
        code, discount = args[1].strip().upper(), int(args[2])
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO promos (code, discount) VALUES (?, ?)", (code, discount))
        conn.commit()
        conn.close()
        await message.answer(f"✅ Promo qo'shildi: {code} ({discount:,} so'm)", parse_mode="HTML")
      
