"""Telegram-бот агентства наружной рекламы: услуги, FAQ и приём заявок."""

import asyncio
import html
import logging
import os
import re
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction
from aiogram.filters import Command, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from dotenv import load_dotenv

import ai
import content
from leads import save_lead

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")  # кому пересылать заявки

dp = Dispatcher()


# ---------- Клавиатуры ----------

BTN_SERVICES = "📋 Услуги и цены"
BTN_FAQ = "❓ Частые вопросы"
BTN_LEAD = "✍️ Оставить заявку"
BTN_CONTACTS = "📞 Контакты"
BTN_CANCEL = "❌ Отмена"

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=BTN_SERVICES), KeyboardButton(text=BTN_FAQ)],
        [KeyboardButton(text=BTN_LEAD), KeyboardButton(text=BTN_CONTACTS)],
    ],
    resize_keyboard=True,
)

cancel_menu = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=BTN_CANCEL)]],
    resize_keyboard=True,
)

phone_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Отправить мой номер", request_contact=True)],
        [KeyboardButton(text=BTN_CANCEL)],
    ],
    resize_keyboard=True,
)


def services_keyboard(prefix: str) -> InlineKeyboardMarkup:
    """Кнопки услуг. prefix отличает «посмотреть» от «выбрать в заявке»."""
    rows = [
        [InlineKeyboardButton(text=title, callback_data=f"{prefix}:{key}")]
        for key, (title, _) in content.SERVICES.items()
    ]
    if prefix == "pick":
        rows.append([InlineKeyboardButton(text="🤷 Пока не знаю", callback_data="pick:unknown")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# ---------- Меню ----------

@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    ai.reset(message.from_user.id)
    await message.answer(content.WELCOME, reply_markup=main_menu)


@dp.message(Command("myid"))
async def cmd_myid(message: Message):
    """Показывает ID чата — нужен, чтобы указать ADMIN_CHAT_ID в .env."""
    await message.answer(f"ID этого чата: <code>{message.chat.id}</code>")


@dp.message(F.text == BTN_SERVICES)
async def show_services(message: Message):
    await message.answer("Выберите услугу:", reply_markup=services_keyboard("info"))


@dp.callback_query(F.data.startswith("info:"))
async def show_service_details(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    _, description = content.SERVICES[key]
    order_button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="✍️ Заказать", callback_data=f"order:{key}")]]
    )
    await callback.message.answer(description, reply_markup=order_button)
    await callback.answer()


@dp.message(F.text == BTN_FAQ)
async def show_faq(message: Message):
    await message.answer(content.FAQ)


@dp.message(F.text == BTN_CONTACTS)
async def show_contacts(message: Message):
    await message.answer(content.CONTACTS)


# ---------- Заявка: имя → телефон → услуга → комментарий ----------

class LeadForm(StatesGroup):
    name = State()
    phone = State()
    service = State()
    comment = State()


@dp.message(F.text == BTN_CANCEL)
async def cancel_lead(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Заявка отменена.", reply_markup=main_menu)


@dp.message(F.text == BTN_LEAD)
async def start_lead(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(LeadForm.name)
    await message.answer("Как к вам обращаться?", reply_markup=cancel_menu)


@dp.callback_query(F.data.startswith("order:"))
async def start_lead_from_service(callback: CallbackQuery, state: FSMContext):
    """Кнопка «Заказать» под услугой — услугу уже знаем, спросим её не будем."""
    key = callback.data.split(":", 1)[1]
    await state.clear()
    await state.update_data(service=content.SERVICES[key][0])
    await state.set_state(LeadForm.name)
    await callback.message.answer("Отлично! Как к вам обращаться?", reply_markup=cancel_menu)
    await callback.answer()


@dp.message(LeadForm.name, F.text)
async def lead_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await state.set_state(LeadForm.phone)
    await message.answer(
        "Ваш номер телефона? Нажмите кнопку ниже или напишите вручную.",
        reply_markup=phone_menu,
    )


@dp.message(LeadForm.phone)
async def lead_phone(message: Message, state: FSMContext):
    if message.contact:
        phone = message.contact.phone_number
    else:
        phone = (message.text or "").strip()
        if len(re.sub(r"\D", "", phone)) < 10:
            await message.answer("Похоже, номер неполный. Напишите, пожалуйста, ещё раз — например +7 900 123-45-67.")
            return

    await state.update_data(phone=phone)
    data = await state.get_data()

    if "service" in data:  # услугу выбрали заранее кнопкой «Заказать»
        await ask_comment(message, state)
    else:
        await state.set_state(LeadForm.service)
        await message.answer("Какая услуга интересует?", reply_markup=ReplyKeyboardRemove())
        await message.answer("Выберите вариант:", reply_markup=services_keyboard("pick"))


@dp.callback_query(LeadForm.service, F.data.startswith("pick:"))
async def lead_service(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    service = content.SERVICES[key][0] if key in content.SERVICES else "Не определился"
    await state.update_data(service=service)
    await callback.answer()
    await ask_comment(callback.message, state)


async def ask_comment(message: Message, state: FSMContext):
    await state.set_state(LeadForm.comment)
    skip = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Пропустить")], [KeyboardButton(text=BTN_CANCEL)]],
        resize_keyboard=True,
    )
    await message.answer(
        "Опишите задачу в паре слов: район, сроки, бюджет. Или нажмите «Пропустить».",
        reply_markup=skip,
    )


@dp.message(LeadForm.comment, F.text)
async def lead_comment(message: Message, state: FSMContext, bot: Bot):
    comment = "" if message.text == "Пропустить" else message.text.strip()
    data = await state.get_data()
    await state.clear()

    lead = {
        "user_id": message.from_user.id,
        "username": message.from_user.username or "",
        "name": data["name"],
        "phone": data["phone"],
        "service": data["service"],
        "comment": comment,
    }
    save_lead(lead)

    await message.answer(
        "✅ Спасибо! Заявка принята, менеджер свяжется с вами в течение часа в рабочее время.",
        reply_markup=main_menu,
    )

    if ADMIN_CHAT_ID:
        username = f"@{lead['username']}" if lead["username"] else "—"
        await bot.send_message(
            ADMIN_CHAT_ID,
            "🔔 <b>Новая заявка</b>\n\n"
            f"👤 {lead['name']} ({username})\n"
            f"📞 {lead['phone']}\n"
            f"📋 {lead['service']}\n"
            f"💬 {lead['comment'] or '—'}",
        )


# ---------- Свободный текст → ИИ-консультант ----------
# Регистрируется последним и только вне анкеты, чтобы не перехватывать ответы в заявке.

@dp.message(StateFilter(None), F.text)
async def ai_answer(message: Message, bot: Bot):
    if not ai.is_enabled():
        await message.answer("Выберите пункт меню 👇", reply_markup=main_menu)
        return

    await bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    answer, wants_lead = await ai.ask(message.from_user.id, message.text)

    markup = None
    if wants_lead:
        markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="✍️ Оставить заявку", callback_data="lead")]]
        )
    await message.answer(html.escape(answer), reply_markup=markup)


@dp.callback_query(F.data == "lead")
async def start_lead_from_ai(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    await start_lead(callback.message, state)


# ---------- Запуск ----------

async def main():
    if not BOT_TOKEN:
        raise SystemExit("Не найден BOT_TOKEN. Скопируйте .env.example в .env и вставьте токен.")

    # Лог пишется в bot.log; в консоль — только если она есть (при фоновом запуске её нет)
    handlers = [RotatingFileHandler(
        Path(__file__).parent / "bot.log", maxBytes=1_000_000, backupCount=3, encoding="utf-8"
    )]
    if sys.stderr:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=handlers,
    )
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
