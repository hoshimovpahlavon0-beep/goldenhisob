import asyncio
import json
import logging
import os

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

# ============================================================
# SOZLAMALAR
# ============================================================

BOT_TOKEN = os.getenv("BOT_TOKEN")

# O'z Telegram ID raqamingni yoz.
# Bir nechta admin bo'lsa, vergul bilan ajrat:
# ADMIN_IDS = [123456789, 987654321]
ADMIN_IDS = [8338181464, 5106574414]

DATA_FILE = "products.json"

logging.basicConfig(level=logging.INFO)

# ============================================================
# BOT
# ============================================================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# MA'LUMOTLAR
# ============================================================

def load_products():
    if not os.path.exists(DATA_FILE):
        return {}

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {}


def save_products(products):
    with open(DATA_FILE, "w", encoding="utf-8") as file:
        json.dump(products, file, ensure_ascii=False, indent=4)


products = load_products()

# ============================================================
# ADMIN TEKSHIRISH
# ============================================================

def is_admin(user_id):
    return user_id in ADMIN_IDS

# ============================================================
# KLAVIATURALAR
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
        ],
        resize_keyboard=True,
    )


def cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Bekor qilish")],
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


class DeleteProduct(StatesGroup):
    product = State()

# ============================================================
# /start
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
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return

    name = (message.text or "").strip()

    if not name:
        await message.answer("❌ Tovar nomini kiriting.")
        return

    if name in products:
        await message.answer(
            "❌ Bu nomdagi tovar allaqachon mavjud.\n"
            "Boshqa nom kiriting."
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
        "Masalan:\n"
        "5000"
    )


@dp.message(AddProduct.cost_price)
async def add_product_cost(message: Message, state: FSMContext):
    try:
        cost = float((message.text or "").replace(",", ".").strip())
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
        "Masalan:\n"
        "8000"
    )


@dp.message(AddProduct.selling_price)
async def add_product_selling(message: Message, state: FSMContext):
    try:
        selling = float((message.text or "").replace(",", ".").strip())
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

    save_products(products)
    await state.clear()

    await message.answer(
        "✅ Tovar muvaffaqiyatli qo'shildi!\n\n"
        f"📦 Tovar: {name}\n"
        f"📥 Boshlang'ich: {initial_quantity} dona\n"
        f"📦 Qoldiq: {initial_quantity} dona\n"
        f"💵 Tannarx: {cost_price:,.0f} so'm\n"
        f"💰 Sotuv narxi: {selling:,.0f} so'm\n\n"
        "📉 Keyin faqat qolgan sonni kiritsangiz,\n"
        "bot sotilgan sonni o'zi hisoblaydi.",
        reply_markup=admin_menu(),
    )

# ============================================================
# QOLDIQNI KIRITISH
# ============================================================

@dp.message(F.text == "📉 Qoldiqni kiritish")
async def remaining_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer("📦 Hozircha tovarlar mavjud emas.")
        return

    text = "📦 Tovarni tanlang:\n\n"

    for i, name in enumerate(products.keys(), 1):
        item = products[name]
        text += (
            f"{i}. {name} — "
            f"hozirgi qoldiq: {item['remaining_quantity']} dona\n"
        )

    text += (
        "\nTovar nomini aynan yozing.\n"
        "Masalan: Sosiska"
    )

    await state.set_state(RemainingProduct.product)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(RemainingProduct.product)
async def remaining_product(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return

    name = (message.text or "").strip()

    if name not in products:
        await message.answer(
            "❌ Bunday tovar topilmadi.\n\n"
            "Tovar nomini to'g'ri yozing."
        )
        return

    await state.update_data(product=name)
    await state.set_state(RemainingProduct.remaining)

    old_remaining = products[name]["remaining_quantity"]

    await message.answer(
        f"📦 {name}\n\n"
        f"Oldingi qoldiq: {old_remaining} dona\n\n"
        "Hozir nechta qolganini kiriting:\n\n"
        "Masalan:\n"
        "3"
    )


@dp.message(RemainingProduct.remaining)
async def remaining_value(message: Message, state: FSMContext):
    try:
        remaining = int((message.text or "").strip())
        if remaining < 0:
            raise ValueError
    except (ValueError, TypeError):
        await message.answer(
            "❌ Faqat 0 yoki musbat son kiriting.\n"
            "Masalan: 3"
        )
        return

    data = await state.get_data()
    name = data["product"]
    product = products[name]

    initial = product["initial_quantity"]

    if remaining > initial:
        await message.answer(
            f"❌ Qoldiq boshlang'ich miqdordan ko'p bo'lishi mumkin emas.\n\n"
            f"Boshlang'ich: {initial} dona"
        )
        return

    sold = initial - remaining

    product["remaining_quantity"] = remaining
    save_products(products)

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
        f"📉 Hozirgi qoldiq: {remaining} dona\n"
        f"📤 Sotilgan: {sold} dona\n\n"
        f"💵 1 dona tannarxi: {cost_price:,.0f} so'm\n"
        f"💰 1 dona sotuv narxi: {selling_price:,.0f} so'm\n\n"
        f"💵 Tushum: {revenue:,.0f} so'm\n"
        f"🧾 Sotilgan mahsulot tannarxi: {total_cost:,.0f} so'm\n"
        f"💰 Foyda: {profit:,.0f} so'm",
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
            f"   📥 Kirim: {initial} dona\n"
            f"   📤 Sotilgan: {sold} dona\n"
            f"   📦 Qoldiq: {remaining} dona\n"
            f"   💵 Tannarx: {item['cost_price']:,.0f} so'm\n"
            f"   💰 Sotuv: {item['selling_price']:,.0f} so'm\n\n"
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
        await message.answer("📊 Hisobot uchun ma'lumot yo'q.")
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
            f"💵 Tannarx: {cost:,.0f} so'm\n"
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
        await message.answer("💰 Hozircha ma'lumot yo'q.")
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
async def delete_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return

    if not products:
        await message.answer("📦 O'chirish uchun tovar yo'q.")
        return

    text = "🗑 O'chirmoqchi bo'lgan tovar nomini yozing:\n\n"

    for name in products:
        text += f"🔹 {name}\n"

    await state.set_state(DeleteProduct.product)
    await message.answer(text, reply_markup=cancel_keyboard())


@dp.message(DeleteProduct.product)
async def delete_product(message: Message, state: FSMContext):
    if message.text == "❌ Bekor qilish":
        await state.clear()
        await message.answer("Bekor qilindi.", reply_markup=admin_menu())
        return

    name = (message.text or "").strip()

    if name not in products:
        await message.answer("❌ Bunday tovar topilmadi.")
        return

    del products[name]
    save_products(products)

    await state.clear()

    await message.answer(
        f"🗑 {name} o'chirildi.",
        reply_markup=admin_menu(),
    )

# ============================================================
# BEKOR QILISH
# ============================================================

@dp.message(F.text == "❌ Bekor qilish")
async def cancel_all(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ Amal bekor qilindi.",
        reply_markup=admin_menu(),
    )

# ============================================================
# BOTNI ISHGA TUSHIRISH
# ============================================================

async def main():
    if not BOT_TOKEN:
        print("❌ BOT_TOKEN topilmadi!")
        return

    print("🤖 Golden Hisobot bot ishga tushdi...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

