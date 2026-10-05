import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import sqlite3
import os
from datetime import datetime

# إعدادات البيئة (يمكن تعديلها مباشرة هنا بدلاً من ملف config.py)
BOT_TOKEN = "8827353783:AAFcK3IM8G1Q4oWhcLhyHAyLUa__cLXmJIQ"  # ضع توكين البوت هنا
ADMIN_ID = 7221322787  # ضع ID المشرف هنا

# إعداد قاعدة البيانات
def init_db():
    conn = sqlite3.connect('roulette_fern.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        is_premium INTEGER DEFAULT 0,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS groups (
        id INTEGER PRIMARY KEY,
        group_id INTEGER UNIQUE,
        title TEXT,
        is_active INTEGER DEFAULT 1,
        linked_by INTEGER,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS draws (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        creator_id INTEGER,
        group_id INTEGER,
        title TEXT,
        description TEXT,
        winners_count INTEGER DEFAULT 1,
        has_captcha INTEGER DEFAULT 1,
        is_auto_draw INTEGER DEFAULT 0,
        is_premium_only INTEGER DEFAULT 0,
        has_ticket_system INTEGER DEFAULT 0,
        lock_old_members INTEGER DEFAULT 0,
        has_join_notifications INTEGER DEFAULT 1,
        conditions TEXT DEFAULT '{}',
        status TEXT DEFAULT 'draft',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        ends_at TEXT
    )
    ''')
    conn.commit()
    conn.close()

# حالات آلة الحالة (FSM)
class DrawCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_conditions = State()
    waiting_for_winners_count = State()
    waiting_for_group_link = State()

# دوال مساعدة
def format_text(text: str) -> str:
    return f"<blockquote>{text}</blockquote>"

def welcome_message() -> str:
    return (
        "<b>أهلاً بك في روليت فيرن...</b>\n\n"
        "هذا البوت سيساعدك في إدارة السحوبات والمسابقات باحترافية!\n\n"
        "<blockquote>تم انشاء البوت بواسطه برونو @bronoIQ</blockquote>"
    )

def main_menu() -> InlineKeyboardMarkup:
    builder = types.InlineKeyboardBuilder()
    buttons = [
        [types.InlineKeyboardButton(text="🎯 انشاء روليت", callback_data="create_roulette")],
        [types.InlineKeyboardButton(text="🎲 الروليت السريع", callback_data="quick_roulette")],
        [types.InlineKeyboardButton(text="📁 سجل القناة", callback_data="channel_logs")],
        [types.InlineKeyboardButton(text="🎰 سحوباتي", callback_data="my_draws")],
        [types.InlineKeyboardButton(text="🔥 التبرع", callback_data="donate")],
        [types.InlineKeyboardButton(text="📊 الإحصائيات", callback_data="stats")],
        [types.InlineKeyboardButton(text="📜 الشروط والأحكام", callback_data="terms")],
        [types.InlineKeyboardButton(text="🔐 الخصوصية", callback_data="privacy")],
        [types.InlineKeyboardButton(text="🛠 الدعم الفني", callback_data="support")],
        [types.InlineKeyboardButton(text="🔔 ذكرني إذا فزت", callback_data="remind_wins")],
        [types.InlineKeyboardButton(text="🎯 أنشئ مسابقة", callback_data="create_draw")]
    ]
    builder.add(*[button for row in buttons for button in row])
    return builder.as_markup()

# معالجات الأوامر
async def start_command(message: types.Message):
    conn = sqlite3.connect('roulette_fern.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (id, username) VALUES (?, ?)',
                  (message.from_user.id, message.from_user.username))
    conn.commit()
    conn.close()

    await message.answer(
        welcome_message(),
        reply_markup=main_menu(),
        parse_mode="HTML"
    )

async def groupid_command(message: types.Message):
    if message.chat.type in ['group', 'supergroup']:
        await message.answer(
            format_text(f"معرف المجموعة: <code>{message.chat.id}</code>\n\n"
                       "ارسل هذا المعرف لي في المحادثة الخاصة للربط"),
            parse_mode="HTML"
        )

# معالجات الأزرار
async def handle_callback(callback: types.CallbackQuery):
    if callback.data == "create_draw":
        await callback.message.edit_text(
            format_text("يرجى إدخال عنوان المسابقة"),
            reply_markup=types.ReplyKeyboardRemove(),
            parse_mode="HTML"
        )
        await DrawCreationStates.waiting_for_title.set()

# معالجات حالات آلة الحالة
async def process_draw_title(message: types.Message, state: FSMContext):
    await state.update_data(title=message.text)
    await state.set_state(DrawCreationStates.waiting_for_description)
    await message.answer(format_text("يرجى إدخال وصف المسابقة"))

async def process_draw_description(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(DrawCreationStates.waiting_for_conditions)
    await message.answer(
        format_text("اختر شروط الدخول للمسابقة"),
        reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="📁 قناة الشرط", callback_data="condition_channel")],
            [types.InlineKeyboardButton(text="⚡ تعزيز قناة", callback_data="condition_boost")],
            [types.InlineKeyboardButton(text="تخطي", callback_data="skip_conditions")],
            [types.InlineKeyboardButton(text="رجوع 🔙", callback_data="back_to_menu")]
        ]),
        parse_mode="HTML"
    )

async def main():
    init_db()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    # تسجيل المعالجات
    dp.message.register(start_command, Command("start"))
    dp.message.register(groupid_command, Command("groupid"))
    dp.message.register(process_draw_title, DrawCreationStates.waiting_for_title)
    dp.message.register(process_draw_description, DrawCreationStates.waiting_for_description)
    dp.callback_query.register(handle_callback)

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
