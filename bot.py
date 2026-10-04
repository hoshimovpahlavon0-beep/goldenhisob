import asyncio
import json
import os
import logging
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

ADMIN_IDS = [8338181464, 5106574414]

PRODUCTS_FILE = "products.json"
CASH_FILE = "daily_reports.json"

logging.basicConfig(level=logging.INFO)


# ============================================================
# MA'LUMOTLAR
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
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=4
        )


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
                KeyboardButton(text="📥 Skladga qo'shish"),
            ],
            [
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
                KeyboardButton(text="🔓 Kassani ochish"),
            ],
            [
                KeyboardButton(text="💸 Rasxod"),
                KeyboardButton(text="✏️ Kassani tahrirlash"),
            ],
            [
                KeyboardButton(text="✏️ Rasxodni tahrirlash"),
                KeyboardButton(text="🗑 Rasxodni o'chirish"),
            ],
            [
                KeyboardButton(text="🔒 Kassani yopish"),
            ],
            [
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
# FSM HOLATLARI
# ============================================================

class AddProduct(StatesGroup):
    name = State()
    initial_quantity = State()
    cost_price = State()
    selling_price = State()


class RemainingProduct(StatesGroup):
    product = State()
    remaining = State()


class AddStock(StatesGroup):
    product = State()
    quantity = State()


class DeleteProduct(StatesGroup):
    product = State()


class OpenCash(StatesGroup):
    amount = State()
    note = State()


class Expense(StatesGroup):
    amount = State()
    note = State()


class EditCash(StatesGroup):
    choice = State()
    amount = State()
    note = State()


class EditExpense(StatesGroup):
    index = State()
    amount = State()
    note = State()


class DeleteExpense(StatesGroup):
    index = State()


# ============================================================
# START
# ============================================================

@dp.message(CommandStart())
async def start(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer(
            "❌ Sizda admin huquqi yo'q."
        )
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
async def add_product_start(
    message: Message,
    state: FSMContext
):
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
async def add_product_name(
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

    if not name:
        await message.answer(
            "❌ Tovar nomini kiriting."
        )
        return

    if name in products:
        await message.answer(
            "❌ Bu nomdagi tovar allaqachon mavjud.\n"
            "Boshqa nom kiriting."
        )
        return

    await state.update_data(name=name)
    await state.set_state(
        AddProduct.initial_quantity
    )

    await message.answer(
        f"📦 {name}\n\n"
        "Boshlang'ich miqdorni kiriting.\n\n"
        "Masalan: 10"
    )


@dp.message(AddProduct.initial_quantity)
async def add_product_quantity(
    message: Message,
    state: FSMContext
):
    try:
        quantity = int(
            (message.text or "").strip()
        )

        if quantity < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Faqat 0 yoki musbat son kiriting.\n"
            "Masalan: 10"
        )
        return

    await state.update_data(
        initial_quantity=quantity
    )

    await state.set_state(
        AddProduct.cost_price
    )

    await message.answer(
        "💵 Tannarxni kiriting.\n\n"
        "Masalan: 5000"
    )


@dp.message(AddProduct.cost_price)
async def add_product_cost(
    message: Message,
    state: FSMContext
):
    try:
        cost = float(
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if cost < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Tannarxni to'g'ri kiriting.\n"
            "Masalan: 5000"
        )
        return

    await state.update_data(
        cost_price=cost
    )

    await state.set_state(
        AddProduct.selling_price
    )

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
            (message.text or "")
            .replace(",", ".")
            .strip()
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

    save_json(
        PRODUCTS_FILE,
        products
    )

    await state.clear()

    await message.answer(
        "✅ Tovar muvaffaqiyatli qo'shildi!\n\n"
        f"📦 Tovar: {name}\n"
        f"📥 Boshlang'ich: "
        f"{initial_quantity} dona\n"
        f"📦 Qoldiq: "
        f"{initial_quantity} dona\n"
        f"💵 Tannarx: "
        f"{cost_price:,.0f} so'm\n"
        f"💰 Sotuv narxi: "
        f"{selling:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# SKLADGA QO'SHISH
# ============================================================

@dp.message(F.text == "📥 Skladga qo'shish")
async def add_stock_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer("📦 Hozircha tovarlar mavjud emas.")
        return

    text = "📦 Skladga qo'shiladigan tovarni tanlang:\n\n"
    for i, name in enumerate(products.keys(), 1):
        item = products[name]
        text += f"{i}. {name} — qoldiq: {item['remaining_quantity']} dona\n"

    text += "\nTovar nomini aynan yozing.\nMasalan: Sosiska"

    await state.set_state(AddStock.product)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(AddStock.product)
async def add_stock_product(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return

    name = (message.text or "").strip()
    if name not in products:
        await message.answer("❌ Bunday tovar topilmadi.")
        return

    await state.update_data(product=name)
    await state.set_state(AddStock.quantity)
    await message.answer(
        f"📦 {name}\n\nQancha dona qo'shasiz?\nMasalan: 10",
        reply_markup=cancel_keyboard(),
    )


@dp.message(AddStock.quantity)
async def add_stock_quantity(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return

    try:
        quantity = int((message.text or "").strip())
    except ValueError:
        await message.answer("❌ Miqdorni faqat son bilan kiriting. Masalan: 10")
        return

    if quantity <= 0:
        await message.answer("❌ Miqdor 0 dan katta bo'lishi kerak.")
        return

    data = await state.get_data()
    name = data["product"]
    item = products[name]

    # Yangi kirimni ham boshlang'ich miqdorga, ham qoldiqqa qo'shamiz.
    # Shunda avval sotilgan tovarlar soni o'zgarmaydi.
    item["initial_quantity"] += quantity
    item["remaining_quantity"] += quantity
    save_json(PRODUCTS_FILE, products)

    await state.clear()
    await message.answer(
        "✅ Skladga qo'shildi!\n\n"
        f"📦 Tovar: {name}\n"
        f"➕ Qo'shildi: {quantity} dona\n"
        f"📦 Yangi qoldiq: {item['remaining_quantity']} dona",
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

    text = "📦 SKLAD QOLDIQLARI\n\n"
    total_remaining = 0

    for i, (name, item) in enumerate(products.items(), 1):
        remaining = item.get("remaining_quantity", 0)
        total_remaining += remaining
        text += f"{i}. 🔹 {name} — 📦 Qoldiq: {remaining} dona\n"

    text += f"\n📊 Jami qoldiq: {total_remaining} dona"

    await message.answer(text, reply_markup=admin_menu())


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

    for i, name in enumerate(
        products.keys(),
        1
    ):
        item = products[name]

        text += (
            f"{i}. {name} — "
            f"qoldiq: "
            f"{item['remaining_quantity']} dona\n"
        )

    text += (
        "\nTovar nomini aynan yozing.\n"
        "Masalan: Sosiska"
    )

    await state.set_state(
        RemainingProduct.product
    )

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

    await state.update_data(
        product=name
    )

    await state.set_state(
        RemainingProduct.remaining
    )

    old_remaining = products[name][
        "remaining_quantity"
    ]

    await message.answer(
        f"📦 {name}\n\n"
        f"Oldingi qoldiq: "
        f"{old_remaining} dona\n\n"
        "Hozir nechta qolganini kiriting."
    )


@dp.message(RemainingProduct.remaining)
async def remaining_value(
    message: Message,
    state: FSMContext
):
    try:
        remaining = int(
            (message.text or "").strip()
        )

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

    initial = product[
        "initial_quantity"
    ]

    if remaining > initial:
        await message.answer(
            "❌ Qoldiq boshlang'ich "
            "miqdordan ko'p bo'lishi mumkin emas."
        )
        return

    sold = initial - remaining

    product[
        "remaining_quantity"
    ] = remaining

    save_json(
        PRODUCTS_FILE,
        products
    )

    cost_price = product[
        "cost_price"
    ]

    selling_price = product[
        "selling_price"
    ]

    revenue = sold * selling_price
    total_cost = sold * cost_price
    profit = revenue - total_cost

    await state.clear()

    await message.answer(
        "✅ Qoldiq saqlandi!\n\n"
        f"📦 Tovar: {name}\n"
        f"📥 Boshlang'ich: "
        f"{initial} dona\n"
        f"📦 Qoldiq: "
        f"{remaining} dona\n"
        f"📤 Sotilgan: "
        f"{sold} dona\n\n"
        f"💵 Tannarx: "
        f"{cost_price:,.0f} so'm\n"
        f"💰 Sotuv narxi: "
        f"{selling_price:,.0f} so'm\n"
        f"💰 Tushum: "
        f"{revenue:,.0f} so'm\n"
        f"📈 Foyda: "
        f"{profit:,.0f} so'm",
        reply_markup=admin_menu(),
    )


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
        initial = item[
            "initial_quantity"
        ]

        remaining = item[
            "remaining_quantity"
        ]

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
            f"📥 Boshlang'ich: "
            f"{initial} dona\n"
            f"📤 Sotilgan: "
            f"{sold} dona\n"
            f"📦 Qoldiq: "
            f"{remaining} dona\n"
            f"💰 Tushum: "
            f"{revenue:,.0f} so'm\n"
            f"📈 Foyda: "
            f"{profit:,.0f} so'm\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        "📊 JAMI\n\n"
        f"📤 Jami sotilgan: "
        f"{total_sold} dona\n"
        f"💰 Jami tushum: "
        f"{total_revenue:,.0f} so'm\n"
        f"🧾 Jami tannarx: "
        f"{total_cost:,.0f} so'm\n"
        f"📈 Jami foyda: "
        f"{total_profit:,.0f} so'm"
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
        initial = item[
            "initial_quantity"
        ]

        remaining = item[
            "remaining_quantity"
        ]

        sold = initial - remaining

        cost = item["cost_price"]
        selling = item["selling_price"]

        revenue = sold * selling
        total_cost = sold * cost
        profit = revenue - total_cost

        total_profit += profit

        text += (
            f"🔹 {name}\n"
            f"📤 Sotilgan: "
            f"{sold} dona\n"
            f"💵 Tannarx: "
            f"{total_cost:,.0f} so'm\n"
            f"💰 Tushum: "
            f"{revenue:,.0f} so'm\n"
            f"📈 Foyda: "
            f"{profit:,.0f} so'm\n\n"
        )

    text += (
        "━━━━━━━━━━━━━━\n"
        f"💰 JAMI FOYDA: "
        f"{total_profit:,.0f} so'm"
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

    text = (
        "🗑 O'chirmoqchi bo'lgan "
        "tovar nomini yozing:\n\n"
    )

    for name in products:
        text += f"🔹 {name}\n"

    await state.set_state(
        DeleteProduct.product
    )

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

    save_json(
        PRODUCTS_FILE,
        products
    )

    await state.clear()

    await message.answer(
        f"🗑 {name} o'chirildi.",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🔓 KASSANI OCHISH
# ============================================================

@dp.message(F.text == "🔓 Kassani ochish")
async def open_cash_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    # Agar bugungi kassa mavjud bo'lsa
    if today in cash_data:
        if cash_data[today].get("closed"):
            await message.answer(
                "🔒 Bugungi kassa allaqachon yopilgan.\n\n"
                f"📅 Sana: {today}\n\n"
                "Yopilgan kassani qayta ochib bo'lmaydi."
            )
            return

        await message.answer(
            "🟢 Bugungi kassa allaqachon ochilgan.\n\n"
            "🧾 Kunlik kassa tugmasi orqali "
            "holatini ko'rishingiz mumkin."
        )
        return

    await state.set_state(
        OpenCash.amount
    )

    await message.answer(
        "🔓 KASSANI OCHISH\n\n"
        f"📅 Sana: {today}\n\n"
        "Boshlang'ich kassa summasini kiriting.\n\n"
        "Masalan:\n"
        "500000",
        reply_markup=cancel_keyboard(),
    )


@dp.message(OpenCash.amount)
async def open_cash_amount(
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
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if amount < 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Summani to'g'ri kiriting.\n"
            "Masalan: 500000"
        )
        return

    await state.update_data(
        opening_cash=amount
    )

    await state.set_state(
        OpenCash.note
    )

    await message.answer(
        "📝 Kassa izohini kiriting.\n\n"
        "Masalan:\n"
        "Bugungi boshlang'ich kassa\n\n"
        "Izoh kerak bo'lmasa:\n"
        "yo'q"
    )


@dp.message(OpenCash.note)
async def open_cash_note(
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

    if note.lower() in [
        "yo'q",
        "yoq",
        "-"
    ]:
        note = ""

    data = await state.get_data()

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    cash_data[today] = {
        "date": today,
        "opening_cash": data[
            "opening_cash"
        ],
        "revenue": 0,
        "expenses": [],
        "expenses_total": 0,
        "closing_cash": data[
            "opening_cash"
        ],
        "note": note,
        "closed": False,
        "opened_time": datetime.now().strftime(
            "%H:%M:%S"
        ),
    }

    save_json(
        CASH_FILE,
        cash_data
    )

    await state.clear()

    await message.answer(
        "✅ KASSA OCHILDI!\n\n"
        f"📅 Sana: {today}\n"
        f"💵 Boshlang'ich kassa: "
        f"{data['opening_cash']:,.0f} so'm\n"
        f"📝 Izoh: "
        f"{note or 'Izoh yo‘q'}",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🧾 KUNLIK KASSA
# ============================================================

@dp.message(F.text == "🧾 Kunlik kassa")
async def daily_cash(message: Message):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if today not in cash_data:
        await message.answer(
            "❌ Bugungi kassa hali ochilmagan.\n\n"
            "Avval:\n"
            "🔓 Kassani ochish\n"
            "tugmasini bosing."
        )
        return

    data = cash_data[today]

    revenue = calculate_today_revenue()

    expenses_total = data.get(
        "expenses_total",
        0
    )

    opening_cash = data.get(
        "opening_cash",
        0
    )

    closing_cash = (
        opening_cash
        + revenue
        - expenses_total
    )

    status = (
        "🔒 Yopilgan"
        if data.get("closed")
        else "🟢 Ochiq"
    )

    await message.answer(
        "🧾 KUNLIK KASSA\n\n"
        f"📅 Sana: {today}\n"
        f"{status}\n\n"
        f"💵 Boshlang'ich kassa: "
        f"{opening_cash:,.0f} so'm\n"
        f"💰 Tushum: "
        f"{revenue:,.0f} so'm\n"
        f"💸 Rasxod: "
        f"{expenses_total:,.0f} so'm\n"
        f"💵 Kassa oxiri: "
        f"{closing_cash:,.0f} so'm\n\n"
        f"📝 Izoh: "
        f"{data.get('note') or 'Izoh yo‘q'}"
    )


# ============================================================
# TUSHUMNI HISOBLASH
# ============================================================

def calculate_today_revenue():
    revenue = 0

    for item in products.values():
        initial = item.get(
            "initial_quantity",
            0
        )

        remaining = item.get(
            "remaining_quantity",
            0
        )

        sold = initial - remaining

        if sold > 0:
            revenue += (
                sold
                * item.get(
                    "selling_price",
                    0
                )
            )

    return revenue


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

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if today not in cash_data:
        await message.answer(
            "❌ Avval kassani oching.\n\n"
            "🔓 Kassani ochish tugmasini bosing."
        )
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa yopilgan.\n\n"
            "Yopilgan kassaga rasxod qo'shib bo'lmaydi."
        )
        return

    await state.set_state(
        Expense.amount
    )

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
            (message.text or "")
            .replace(",", ".")
            .strip()
        )

        if amount <= 0:
            raise ValueError

    except (ValueError, TypeError):
        await message.answer(
            "❌ Summani to'g'ri kiriting.\n"
            "Masalan: 50000"
        )
        return

    await state.update_data(
        amount=amount
    )

    await state.set_state(
        Expense.note
    )

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

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

    if today not in cash_data:
        await state.clear()

        await message.answer(
            "❌ Bugungi kassa topilmadi."
        )
        return

    expense_item = {
        "amount": amount,
        "note": note,
        "time": datetime.now().strftime(
            "%H:%M:%S"
        ),
    }

    cash_data[today].setdefault(
        "expenses",
        []
    )

    cash_data[today][
        "expenses"
    ].append(expense_item)

    cash_data[today][
        "expenses_total"
    ] = sum(
        item["amount"]
        for item in cash_data[today][
            "expenses"
        ]
    )

    save_json(
        CASH_FILE,
        cash_data
    )

    await state.clear()

    await message.answer(
        "✅ RASXOD SAQLANDI!\n\n"
        f"💸 Summa: "
        f"{amount:,.0f} so'm\n"
        f"📝 Izoh: {note}\n\n"
        f"💸 Bugungi jami rasxod: "
        f"{cash_data[today]['expenses_total']:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# ✏️ KASSANI TAHRIRLASH
# ============================================================

def cash_edit_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💵 Ochilish summasini o'zgartirish")],
            [KeyboardButton(text="📝 Kassa izohini o'zgartirish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def get_today():
    return datetime.now().strftime("%Y-%m-%d")


@dp.message(F.text == "✏️ Kassani tahrirlash")
async def edit_cash_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = get_today()

    if today not in cash_data:
        await message.answer(
            "❌ Bugungi kassa hali ochilmagan.\n\n"
            "Avval 🔓 Kassani oching."
        )
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa yopilgan.\n\n"
            "Yopilgan kassani tahrirlab bo'lmaydi."
        )
        return

    await state.set_state(EditCash.choice)

    await message.answer(
        "✏️ KASSANI TAHRIRLASH\n\n"
        "Nimani o'zgartirmoqchisiz?",
        reply_markup=cash_edit_keyboard(),
    )


@dp.message(EditCash.choice)
async def edit_cash_choice(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    today = get_today()

    if today not in cash_data or cash_data[today].get("closed"):
        await state.clear()
        await message.answer(
            "🔒 Kassa yopilgan yoki mavjud emas.",
            reply_markup=admin_menu(),
        )
        return

    if message.text == "💵 Ochilish summasini o'zgartirish":
        await state.set_state(EditCash.amount)
        await message.answer(
            "💵 Yangi ochilish summasini kiriting.\n\n"
            "Masalan: 550000",
            reply_markup=cancel_keyboard(),
        )
        return

    if message.text == "📝 Kassa izohini o'zgartirish":
        await state.set_state(EditCash.note)
        await message.answer(
            "📝 Yangi kassa izohini kiriting.\n\n"
            "Izoh kerak bo'lmasa: yo'q",
            reply_markup=cancel_keyboard(),
        )
        return

    await message.answer(
        "❌ Tugmalardan birini tanlang.",
        reply_markup=cash_edit_keyboard(),
    )


@dp.message(EditCash.amount)
async def edit_cash_amount(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
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
            "Masalan: 550000"
        )
        return

    today = get_today()

    if today not in cash_data or cash_data[today].get("closed"):
        await state.clear()
        await message.answer(
            "🔒 Kassa yopilgan yoki mavjud emas.",
            reply_markup=admin_menu(),
        )
        return

    cash_data[today]["opening_cash"] = amount

    revenue = calculate_today_revenue()
    expenses_total = cash_data[today].get("expenses_total", 0)
    cash_data[today]["closing_cash"] = (
        amount + revenue - expenses_total
    )

    save_json(CASH_FILE, cash_data)
    await state.clear()

    await message.answer(
        "✅ Kassa ochilish summasi o'zgartirildi!\n\n"
        f"💵 Yangi summa: {amount:,.0f} so'm\n"
        f"💵 Hozirgi kassa oxiri: "
        f"{cash_data[today]['closing_cash']:,.0f} so'm",
        reply_markup=admin_menu(),
    )


@dp.message(EditCash.note)
async def edit_cash_note(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    note = (message.text or "").strip()

    if note.lower() in ["yo'q", "yoq", "-"]:
        note = ""

    today = get_today()

    if today not in cash_data or cash_data[today].get("closed"):
        await state.clear()
        await message.answer(
            "🔒 Kassa yopilgan yoki mavjud emas.",
            reply_markup=admin_menu(),
        )
        return

    cash_data[today]["note"] = note
    save_json(CASH_FILE, cash_data)
    await state.clear()

    await message.answer(
        "✅ Kassa izohi o'zgartirildi!\n\n"
        f"📝 Izoh: {note or 'Izoh yo‘q'}",
        reply_markup=admin_menu(),
    )


# ============================================================
# ✏️ RASXODNI TAHRIRLASH
# ============================================================

def expense_list_text(today):
    expenses = cash_data[today].get("expenses", [])

    if not expenses:
        return "💸 Bugungi rasxodlar mavjud emas."

    text = "💸 BUGUNGI RASXODLAR\n\n"

    for i, item in enumerate(expenses, 1):
        text += (
            f"{i}. 💸 {item.get('amount', 0):,.0f} so'm\n"
            f"   📝 {item.get('note') or 'Izoh yo‘q'}\n"
            f"   🕐 {item.get('time', '')}\n\n"
        )

    return text


@dp.message(F.text == "✏️ Rasxodni tahrirlash")
async def edit_expense_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = get_today()

    if today not in cash_data:
        await message.answer("❌ Avval kassani oching.")
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa yopilgan.\n\n"
            "Yopilgan kassadagi rasxodni tahrirlab bo'lmaydi."
        )
        return

    expenses = cash_data[today].get("expenses", [])

    if not expenses:
        await message.answer("💸 Bugun rasxod yo'q.")
        return

    await state.set_state(EditExpense.index)

    await message.answer(
        expense_list_text(today) +
        "\n✏️ Qaysi rasxodni tahrirlash kerak?\n"
        "Raqamini kiriting. Masalan: 1",
        reply_markup=cancel_keyboard(),
    )


@dp.message(EditExpense.index)
async def edit_expense_index(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    try:
        index = int((message.text or "").strip()) - 1
    except ValueError:
        await message.answer("❌ Rasxod raqamini to'g'ri kiriting.")
        return

    today = get_today()
    expenses = cash_data.get(today, {}).get("expenses", [])

    if index < 0 or index >= len(expenses):
        await message.answer(
            "❌ Bunday raqamli rasxod yo'q.\n"
            "Masalan: 1"
        )
        return

    await state.update_data(index=index)
    await state.set_state(EditExpense.amount)

    old = expenses[index]

    await message.answer(
        "💸 Yangi rasxod summasini kiriting.\n\n"
        f"Eski summa: {old.get('amount', 0):,.0f} so'm\n\n"
        "Masalan: 80000",
        reply_markup=cancel_keyboard(),
    )


@dp.message(EditExpense.amount)
async def edit_expense_amount(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
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
            "Masalan: 80000"
        )
        return

    await state.update_data(amount=amount)
    await state.set_state(EditExpense.note)

    await message.answer(
        "📝 Yangi rasxod izohini kiriting.\n\n"
        "Masalan: Non va mahsulot olindi",
        reply_markup=cancel_keyboard(),
    )


@dp.message(EditExpense.note)
async def edit_expense_note(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ Tahrirlash bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    note = (message.text or "").strip()
    data = await state.get_data()
    index = data["index"]
    amount = data["amount"]

    today = get_today()

    if today not in cash_data or cash_data[today].get("closed"):
        await state.clear()
        await message.answer(
            "🔒 Kassa yopilgan yoki mavjud emas.",
            reply_markup=admin_menu(),
        )
        return

    expenses = cash_data[today].setdefault("expenses", [])

    if index < 0 or index >= len(expenses):
        await state.clear()
        await message.answer(
            "❌ Rasxod topilmadi.",
            reply_markup=admin_menu(),
        )
        return

    expenses[index]["amount"] = amount
    expenses[index]["note"] = note

    cash_data[today]["expenses_total"] = sum(
        float(item.get("amount", 0))
        for item in expenses
    )

    revenue = calculate_today_revenue()
    opening_cash = cash_data[today].get("opening_cash", 0)

    cash_data[today]["closing_cash"] = (
        opening_cash
        + revenue
        - cash_data[today]["expenses_total"]
    )

    save_json(CASH_FILE, cash_data)
    await state.clear()

    await message.answer(
        "✅ RASXOD TAHRIRLANDI!\n\n"
        f"💸 Yangi summa: {amount:,.0f} so'm\n"
        f"📝 Izoh: {note or 'Izoh yo‘q'}\n\n"
        f"💸 Jami rasxod: "
        f"{cash_data[today]['expenses_total']:,.0f} so'm\n"
        f"💵 Kassa oxiri: "
        f"{cash_data[today]['closing_cash']:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🗑 RASXODNI O'CHIRISH
# ============================================================

@dp.message(F.text == "🗑 Rasxodni o'chirish")
async def delete_expense_start(
    message: Message,
    state: FSMContext
):
    if not is_admin(message.from_user.id):
        return

    today = get_today()

    if today not in cash_data:
        await message.answer("❌ Avval kassani oching.")
        return

    if cash_data[today].get("closed"):
        await message.answer(
            "🔒 Bugungi kassa yopilgan.\n\n"
            "Yopilgan kassadagi rasxodni o'chirib bo'lmaydi."
        )
        return

    expenses = cash_data[today].get("expenses", [])

    if not expenses:
        await message.answer("💸 Bugun o'chirish uchun rasxod yo'q.")
        return

    await state.set_state(DeleteExpense.index)

    await message.answer(
        expense_list_text(today) +
        "\n🗑 Qaysi rasxodni o'chirish kerak?\n"
        "Raqamini kiriting. Masalan: 1",
        reply_markup=cancel_keyboard(),
    )


@dp.message(DeleteExpense.index)
async def delete_expense_index(
    message: Message,
    state: FSMContext
):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer(
            "❌ O'chirish bekor qilindi.",
            reply_markup=admin_menu(),
        )
        return

    try:
        index = int((message.text or "").strip()) - 1
    except ValueError:
        await message.answer("❌ Rasxod raqamini to'g'ri kiriting.")
        return

    today = get_today()

    if today not in cash_data or cash_data[today].get("closed"):
        await state.clear()
        await message.answer(
            "🔒 Kassa yopilgan yoki mavjud emas.",
            reply_markup=admin_menu(),
        )
        return

    expenses = cash_data[today].get("expenses", [])

    if index < 0 or index >= len(expenses):
        await message.answer(
            "❌ Bunday raqamli rasxod yo'q."
        )
        return

    removed = expenses.pop(index)

    cash_data[today]["expenses_total"] = sum(
        float(item.get("amount", 0))
        for item in expenses
    )

    revenue = calculate_today_revenue()
    opening_cash = cash_data[today].get("opening_cash", 0)

    cash_data[today]["closing_cash"] = (
        opening_cash
        + revenue
        - cash_data[today]["expenses_total"]
    )

    save_json(CASH_FILE, cash_data)
    await state.clear()

    await message.answer(
        "🗑 RASXOD O'CHIRILDI!\n\n"
        f"💸 O'chirilgan summa: "
        f"{float(removed.get('amount', 0)):,.0f} so'm\n"
        f"📝 Izoh: "
        f"{removed.get('note') or 'Izoh yo‘q'}\n\n"
        f"💸 Qolgan rasxod: "
        f"{cash_data[today]['expenses_total']:,.0f} so'm\n"
        f"💵 Kassa oxiri: "
        f"{cash_data[today]['closing_cash']:,.0f} so'm",
        reply_markup=admin_menu(),
    )


# ============================================================
# 🔒 KASSANI YOPISH
# ============================================================

@dp.message(F.text == "🔒 Kassani yopish")
async def close_cash(message: Message):
    if not is_admin(message.from_user.id):
        return

    today = datetime.now().strftime(
        "%Y-%m-%d"
    )

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

    revenue = calculate_today_revenue()

    expenses_total = cash_data[
        today
    ].get(
        "expenses_total",
        0
    )

    opening_cash = cash_data[
        today
    ].get(
        "opening_cash",
        0
    )

    closing_cash = (
        opening_cash
        + revenue
        - expenses_total
    )

    cash_data[today][
        "revenue"
    ] = revenue

    cash_data[today][
        "closing_cash"
    ] = closing_cash

    cash_data[today][
        "closed"
    ] = True

    cash_data[today][
        "closed_time"
    ] = datetime.now().strftime(
        "%H:%M:%S"
    )

    save_json(
        CASH_FILE,
        cash_data
    )

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
        f"{cash_data[today].get('note') or 'Izoh yo‘q'}",
        reply_markup=admin_menu(),
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
            "━━━━━━━━━━━━━━\n"
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
    print(
        "🤖 Golden Hisobot bot ishga tushdi..."
    )

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
