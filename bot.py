import asyncio
import json
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton


# ============================================================
# SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# SIZNING ADMIN ID
ADMIN_IDS = [8338181464]

PRODUCTS_FILE = "products.json"
CASH_FILE = "daily_reports.json"

logging.basicConfig(level=logging.INFO)


# ============================================================
# MA'LUMOTLARNI YUKLASH / SAQLASH
# ============================================================

def load_json(filename, default):
    if not os.path.exists(filename):
        return default

    try:
        with open(filename, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return default


def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


products = load_json(PRODUCTS_FILE, {})
cash_data = load_json(CASH_FILE, {})


# ============================================================
# BOT
# ============================================================

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi!")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ============================================================
# ADMIN
# ============================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS


# ============================================================
# ADMIN MENU
# ============================================================

def admin_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Tovar qo'shish"),
                KeyboardButton(text="📦 Sklad"),
            ],
            [
                KeyboardButton(text="📉 Qoldiqni kiritish"),
                KeyboardButton(text="📊 Hisobot"),
            ],
            [
                KeyboardButton(text="💰 Foyda"),
                KeyboardButton(text="🗑 Tovar o'chirish"),
            ],
            [
                KeyboardButton(text="🧾 Kunlik kassa"),
                KeyboardButton(text="💸 Rasxod"),
            ],
            [
                KeyboardButton(text="🔒 Kassani yopish"),
                KeyboardButton(text="📅 Eski kassalar"),
            ],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True,
    )


# ============================================================
# FSM
# ============================================================

class AddProduct(StatesGroup):
    name = State()
    initial_quantity = State()
    cost_price = State()
    selling_price = State()


class RemainingProduct(StatesGroup):
    product = State()
    remaining = State()


class DeleteProduct(StatesGroup):
    product = State()


class CashStart(StatesGroup):
    amount = State()
    note = State()


class Expense(StatesGroup):
    amount = State()
    note = State()


class CashNote(StatesGroup):
    note = State()


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda admin huquqi yo'q.")
        return

    await message.answer(
        "👋 Golden Hisobot botiga xush kelibsiz!\n\n"
        "Kerakli bo'limni tanlang:",
        reply_markup=admin_menu(),
    )


# ============================================================
# TOVAR QO'SHISH
# ============================================================

@dp.message(F.text == "➕ Tovar qo'shish")
async def add_product_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    await state.set_state(AddProduct.name)

    await message.answer(
        "📦 Tovar nomini kiriting:\n\n"
        "Masalan:\n"
        "Sosiska",
        reply_markup=cancel_keyboard(),
    )


@dp.message(AddProduct.name)
async def add_product_name(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    name = (message.text or "").strip()

    if not name:
        await message.answer("❌ Tovar nomini kiriting.")
        return

    if name in products:
        await message.answer(
            "❌ Bu nomdagi tovar allaqachon mavjud."
        )
        return

    await state.update_data(name=name)
    await state.set_state(AddProduct.initial_quantity)

    await message.answer(
        f"📦 {name}\n\n"
        "Boshlang'ich miqdorni kiriting:\n\n"
        "Masalan: 10"
    )


@dp.message(AddProduct.initial_quantity)
async def add_product_quantity(message: Message, state: FSMContext):
    try:
        quantity = int((message.text or "").strip())

        if quantity < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Faqat 0 yoki musbat son kiriting.\n"
            "Masalan: 10"
        )
        return

    await state.update_data(initial_quantity=quantity)
    await state.set_state(AddProduct.cost_price)

    await message.answer(
        "💵 Tannarxni kiriting.\n\n"
        "Masalan: 5000"
    )


@dp.message(AddProduct.cost_price)
async def add_product_cost(message: Message, state: FSMContext):
    try:
        cost = float(
            (message.text or "").replace(",", ".").strip()
        )

        if cost < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Tannarxni to'g'ri kiriting.\n"
            "Masalan: 5000"
        )
        return

    await state.update_data(cost_price=cost)
    await state.set_state(AddProduct.selling_price)

    await message.answer(
        "💰 Sotuv narxini kiriting.\n\n"
        "Masalan: 8000"
    )


@dp.message(AddProduct.selling_price)
async def add_product_selling(
    message: Message,
    state: FSMContext
):
    try:
        selling = float(
            (message.text or "").replace(",", ".").strip()
        )

        if selling < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Sotuv narxini to'g'ri kiriting.\n"
            "Masalan: 8000"
        )
        return

    data = await state.get_data()

    name = data["name"]
    initial_quantity = data["initial_quantity"]
    cost_price = data["cost_price"]

    products[name] = {
        "initial_quantity": initial_quantity,
        "remaining_quantity": initial_quantity,
        "cost_price": cost_price,
        "selling_price": selling,
    }

    save_json(PRODUCTS_FILE, products)

    await state.clear()

    await message.answer(
        "✅ Tovar muvaffaqiyatli qo'shildi!\n\n"
        f"📦 Tovar: {name}\n"
        f"📥 Boshlang'ich: {initial_quantity} dona\n"
        f"📦 Qoldiq: {initial_quantity} dona\n"
        f"💵 Tannarx: {cost_price:,.0f} so'm\n"
        f"💰 Sotuv narxi: {selling:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# QOLDIQNI KIRITISH
# ============================================================

@dp.message(F.text == "📉 Qoldiqni kiritish")
async def remaining_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer(
            "📦 Hozircha tovarlar mavjud emas."
        )
        return

    text = "📦 Tovarni tanlang:\n\n"

    for i, name in enumerate(products.keys(), 1):
        item = products[name]

        text += (
            f"{i}. {name} — "
            f"qoldiq: {item['remaining_quantity']} dona\n"
        )

    text += (
        "\nTovar nomini aynan yozing.\n"
        "Masalan: Sosiska"
    )

    await state.set_state(RemainingProduct.product)

    await message.answer(
        text,
        reply_markup=cancel_keyboard(),
    )


@dp.message(RemainingProduct.product)
async def remaining_product(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    name = (message.text or "").strip()

    if name not in products:
        await message.answer(
            "❌ Bunday tovar topilmadi."
        )
        return

    await state.update_data(product=name)
    await state.set_state(RemainingProduct.remaining)

    old_remaining = products[name]["remaining_quantity"]

    await message.answer(
        f"📦 {name}\n\n"
        f"Oldingi qoldiq: {old_remaining} dona\n\n"
        "Hozir nechta qolganini kiriting:"
    )


@dp.message(RemainingProduct.remaining)
async def remaining_value(
    message: Message,
    state: FSMContext
):
    try:
        remaining = int((message.text or "").strip())

        if remaining < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Faqat 0 yoki musbat son kiriting."
        )
        return

    data = await state.get_data()

    name = data["product"]
    product = products[name]

    initial = product["initial_quantity"]

    if remaining > initial:
        await message.answer(
            "❌ Qoldiq boshlang'ich miqdordan "
            "ko'p bo'lishi mumkin emas."
        )
        return

    sold = initial - remaining

    product["remaining_quantity"] = remaining

    save_json(PRODUCTS_FILE, products)

    cost_price = product["cost_price"]
    selling_price = product["selling_price"]

    revenue = sold * selling_price
    total_cost = sold * cost_price
    profit = revenue - total_cost

    await state.clear()

    await message.answer(
        "✅ Qoldiq saqlandi!\n\n"
        f"📦 Tovar: {name}\n"
        f"📥 Boshlang'ich: {initial} dona\n"
        f"📦 Qoldiq: {remaining} dona\n"
        f"📤 Sotilgan: {sold} dona\n\n"
        f"💵 Tannarx: {cost_price:,.0f} so'm\n"
        f"💰 Sotuv narxi: {selling_price:,.0f} so'm\n"
        f"💰 Tushum: {revenue:,.0f} so'm\n"
        f"📈 Foyda: {profit:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# SKLAD
# ============================================================

@dp.message(F.text == "📦 Sklad")
async def sklad(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer("📦 Sklad bo'sh.")
        return

    text = "📦 SKLAD\n\n"

    for name, item in products.items():
        initial = item["initial_quantity"]
        remaining = item["remaining_quantity"]
        sold = initial - remaining

        text += (
            f"🔹 {name}\n"
            f"📥 Kirim: {initial} dona\n"
            f"📤 Sotilgan: {sold} dona\n"
            f"📦 Qoldiq: {remaining} dona\n"
            f"💵 Tannarx: {item['cost_price']:,.0f} so'm\n"
            f"💰 Sotuv: {item['selling_price']:,.0f} so'm\n\n"
        )

    await message.answer(text)


# ============================================================
# UMUMIY HISOBOT
# ============================================================

@dp.message(F.text == "📊 Hisobot")
async def report(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer(
            "📊 Hisobot uchun ma'lumot yo'q."
        )
        return

    total_revenue = 0
    total_cost = 0
    total_profit = 0
    total_sold = 0

    text = "📊 UMUMIY HISOBOT\n\n"

    for name, item in products.items():
        initial = item["initial_quantity"]
        remaining = item["remaining_quantity"]
        sold = initial - remaining

        cost = item["cost_price"]
        selling = item["selling_price"]

        revenue = sold * selling
        product_cost = sold * cost
        profit = revenue - product_cost

        total_sold += sold
        total_revenue += revenue
        total_cost += product_cost
        total_profit += profit

        text += (
            f"🔹 {name}\n"
            f"📥 Boshlang'ich: {initial} dona\n"
            f"📤 Sotilgan: {sold} dona\n"
            f"📦 Qoldiq: {remaining} dona\n"
            f"💰 Tushum: {revenue:,.0f} so'm\n"
            f"📈 Foyda: {profit:,.0f} so'm\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        "📊 JAMI\n\n"
        f"📤 Jami sotilgan: {total_sold} dona\n"
        f"💰 Jami tushum: {total_revenue:,.0f} so'm\n"
        f"🧾 Jami tannarx: {total_cost:,.0f} so'm\n"
        f"📈 Jami foyda: {total_profit:,.0f} so'm"
    )

    await message.answer(text)


# ============================================================
# FOYDA
# ============================================================

@dp.message(F.text == "💰 Foyda")
async def profit_report(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer(
            "💰 Hozircha ma'lumot yo'q."
        )
        return

    total_profit = 0

    text = "💰 FOYDA HISOBOTI\n\n"

    for name, item in products.items():
        initial = item["initial_quantity"]
        remaining = item["remaining_quantity"]
        sold = initial - remaining

        cost = item["cost_price"]
        selling = item["selling_price"]

        revenue = sold * selling
        total_cost = sold * cost
        profit = revenue - total_cost

        total_profit += profit

        text += (
            f"🔹 {name}\n"
            f"📤 Sotilgan: {sold} dona\n"
            f"💵 Tannarx: {total_cost:,.0f} so'm\n"
            f"💰 Tushum: {revenue:,.0f} so'm\n"
            f"📈 Foyda: {profit:,.0f} so'm\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        f"💰 JAMI FOYDA: {total_profit:,.0f} so'm"
    )

    await message.answer(text)


# ============================================================
# TOVAR O'CHIRISH
# ============================================================

@dp.message(F.text == "🗑 Tovar o'chirish")
async def delete_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer(
            "📦 O'chirish uchun tovar yo'q."
        )
        return

    text = "🗑 O'chirmoqchi bo'lgan tovar nomini yozing:\n\n"

    for name in products:
        text += f"🔹 {name}\n"

    await state.set_state(DeleteProduct.product)

    await message.answer(
        text,
        reply_markup=cancel_keyboard(),
    )


@dp.message(DeleteProduct.product)
async def delete_product(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    name = (message.text or "").strip()

    if name not in products:
        await message.answer(
            "❌ Bunday tovar topilmadi."
        )
        return

    del products[name]

    save_json(PRODUCTS_FILE, products)

    await state.clear()

    await message.answer(
        f"🗑 {name} o'chirildi.",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🧾 KUNLIK KASSA
# ============================================================

@dp.message(F.text == "🧾 Kunlik kassa")
async def daily_cash_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime("%Y-%m-%d")

    if today in cash_data and cash_data[today].get("closed"):
        await message.answer(
            f"🔒 Bugungi kassa allaqachon yopilgan.\n\n"
            f"📅 Sana: {today}\n\n"
            "Agar eski kassalarni ko'rmoqchi bo'lsangiz:\n"
            "📅 Eski kassalar tugmasini bosing."
        )
        return

    if today in cash_data:
        data = cash_data[today]

        await message.answer(
            "🧾 BUGUNGI KASSA\n\n"
            f"📅 Sana: {today}\n"
            f"💵 Boshlang'ich kassa: "
            f"{data.get('opening_cash', 0):,.0f} so'm\n"
            f"💰 Tushum: "
            f"{data.get('revenue', 0):,.0f} so'm\n"
            f"💸 Rasxod: "
            f"{data.get('expenses_total', 0):,.0f} so'm\n"
            f"💵 Kassa oxiri: "
            f"{data.get('closing_cash', 0):,.0f} so'm\n\n"
            f"📝 Izoh: {data.get('note', 'Izoh yo‘q')}"
        )
        return

    await state.set_state(CashStart.amount)

    await message.answer(
        "🧾 KUNLIK KASSA\n\n"
        "Bugungi boshlang'ich kassani kiriting.\n\n"
        "Masalan:\n"
        "500000",
        reply_markup=cancel_keyboard(),
    )


@dp.message(CashStart.amount)
async def cash_start_amount(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    try:
        amount = float(
            (message.text or "").replace(",", ".").strip()
        )

        if amount < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Summani to'g'ri kiriting.\n"
            "Masalan: 500000"
        )
        return

    await state.update_data(opening_cash=amount)
    await state.set_state(CashStart.note)

    await message.answer(
        "📝 Kassa izohini kiriting.\n\n"
        "Masalan:\n"
        "Bugungi boshlang'ich kassa\n\n"
        "Izoh kerak bo'lmasa:\n"
        "yo'q"
    )


@dp.message(CashStart.note)
async def cash_start_note(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    note = (message.text or "").strip()

    if note.lower() == "yo'q":
        note = ""

    data = await state.get_data()

    today = datetime.now().strftime("%Y-%m-%d")

    cash_data[today] = {
        "date": today,
        "opening_cash": data["opening_cash"],
        "revenue": 0,
        "expenses": [],
        "expenses_total": 0,
        "closing_cash": data["opening_cash"],
        "note": note,
        "closed": False,
    }

    save_json(CASH_FILE, cash_data)

    await state.clear()

    await message.answer(
        "✅ Kassa ochildi!\n\n"
        f"📅 Sana: {today}\n"
        f"💵 Boshlang'ich kassa: "
        f"{data['opening_cash']:,.0f} so'm\n"
        f"📝 Izoh: {note or 'Izoh yo‘q'}",
        reply_markup=admin_menu(),
    )


# ============================================================
# 💸 RASXOD
# ============================================================

@dp.message(F.text == "💸 Rasxod")
async def expense_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime("%Y-%m-%d")

    if today not in cash_data:
        await message.answer(
            "❌ Avval bugungi kassani oching.\n\n"
            "🧾 Kunlik kassa tugmasini bosing."
        )
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa yopilgan.\n"
            "Yopilgan kassaga rasxod qo'shib bo'lmaydi."
        )
        return

    await state.set_state(Expense.amount)

    await message.answer(
        "💸 RASXOD\n\n"
        "Rasxod summasini kiriting.\n\n"
        "Masalan:\n"
        "50000",
        reply_markup=cancel_keyboard(),
    )


@dp.message(Expense.amount)
async def expense_amount(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    try:
        amount = float(
            (message.text or "").replace(",", ".").strip()
        )

        if amount <= 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Summani to'g'ri kiriting.\n"
            "Masalan: 50000"
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(Expense.note)

    await message.answer(
        "📝 Rasxod izohini kiriting.\n\n"
        "Masalan:\n"
        "Non va mahsulot olindi"
    )


@dp.message(Expense.note)
async def expense_note(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "Bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    note = (message.text or "").strip()

    data = await state.get_data()

    amount = data["amount"]

    today = datetime.now().strftime("%Y-%m-%d")

    if today not in cash_data:
        await state.clear()

        await message.answer(
            "❌ Bugungi kassa topilmadi."
        )
        return

    expense_item = {
        "amount": amount,
        "note": note,
        "time": datetime.now().strftime("%H:%M:%S"),
    }

    cash_data[today].setdefault("expenses", [])
    cash_data[today]["expenses"].append(expense_item)

    cash_data[today]["expenses_total"] = sum(
        item["amount"]
        for item in cash_data[today]["expenses"]
    )

    save_json(CASH_FILE, cash_data)

    await state.clear()

    await message.answer(
        "✅ Rasxod saqlandi!\n\n"
        f"💸 Summa: {amount:,.0f} so'm\n"
        f"📝 Izoh: {note}\n\n"
        f"💸 Jami bugungi rasxod: "
        f"{cash_data[today]['expenses_total']:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🔒 KASSANI YOPISH
# ============================================================

@dp.message(F.text == "🔒 Kassani yopish")
async def close_cash(message: Message):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime("%Y-%m-%d")

    if today not in cash_data:
        await message.answer(
            "❌ Bugungi kassa hali ochilmagan."
        )
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa allaqachon yopilgan."
        )
        return

    # Tovarlar bo'yicha bugungi tushumni hisoblash
    revenue = 0

    for item in products.values():
        initial = item.get("initial_quantity", 0)
        remaining = item.get("remaining_quantity", 0)

        sold = initial - remaining

        if sold > 0:
            revenue += sold * item.get(
                "selling_price", 0
            )

    expenses_total = cash_data[today].get(
        "expenses_total", 0
    )

    opening_cash = cash_data[today].get(
        "opening_cash", 0
    )

    closing_cash = (
        opening_cash
        + revenue
        - expenses_total
    )

    cash_data[today]["revenue"] = revenue
    cash_data[today]["closing_cash"] = closing_cash
    cash_data[today]["closed"] = True
    cash_data[today]["closed_time"] = datetime.now().strftime(
        "%H:%M:%S"
    )

    save_json(CASH_FILE, cash_data)

    await message.answer(
        "🔒 KASSA YOPILDI!\n\n"
        f"📅 Sana: {today}\n"
        f"💵 Boshlang'ich kassa: "
        f"{opening_cash:,.0f} so'm\n"
        f"💰 Tushum: "
        f"{revenue:,.0f} so'm\n"
        f"💸 Rasxod: "
        f"{expenses_total:,.0f} so'm\n"
        f"💵 Kassa oxiri: "
        f"{closing_cash:,.0f} so'm\n\n"
        f"📝 Izoh: "
        f"{cash_data[today].get('note') or 'Izoh yo‘q'}"
    )


# ============================================================
# 📅 ESKI KASSALAR
# ============================================================

@dp.message(F.text == "📅 Eski kassalar")
async def old_cash_reports(message: Message):
    if not is_admin(message.from_user.id):
        return

    if not cash_data:
        await message.answer(
            "📅 Hozircha saqlangan kassa yo'q."
        )
        return

    text = "📅 SAQLANGAN KASSALAR\n\n"

    for date in sorted(
        cash_data.keys(),
        reverse=True
    ):
        data = cash_data[date]

        status = (
            "🔒 Yopilgan"
            if data.get("closed")
            else "🟢 Ochiq"
        )

        text += (
            f"📅 {date}\n"
            f"{status}\n"
            f"💵 Boshlang'ich: "
            f"{data.get('opening_cash', 0):,.0f} so'm\n"
            f"💰 Tushum: "
            f"{data.get('revenue', 0):,.0f} so'm\n"
            f"💸 Rasxod: "
            f"{data.get('expenses_total', 0):,.0f} so'm\n"
            f"💵 Kassa oxiri: "
            f"{data.get('closing_cash', 0):,.0f} so'm\n"
            f"📝 Izoh: "
            f"{data.get('note') or 'Izoh yo‘q'}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await message.answer(text)


# ============================================================
# ❌ BEKOR QILISH
# ============================================================

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_all(
    message: Message,
    state: FSMContext
):
    await state.clear()

    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=admin_menu(),
    )


# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================

async def main():
    print("🤖 Golden Hisobot bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
