from __future__ import annotations

from io import BytesIO

import qrcode

import asyncio
import logging
import re
from html import escape
from typing import Any

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    BufferedInputFile,
    FSInputFile,
    Message,
)

from config import (
    DELIVERY_METHODS,
    PAYMENT_METHODS,
    SUPPORTED_LANGUAGES,
    settings,
)
from database import (
    add_to_cart,
    clear_cart,
    confirm_qr_payment,
    count_users,
    create_category,
    create_order,
    create_product,
    create_tables,
    delete_category,
    delete_product,
    get_cart,
    get_categories,
    get_category,
    get_order,
    get_order_items,
    get_orders,
    get_payments_for_check,
    get_product,
    get_products,
    get_statistics,
    get_user,
    get_user_language,
    get_user_order_items,
    get_user_orders,
    get_users,
    reject_qr_payment,
    request_payment_check,
    set_cart_quantity,
    set_category_active,
    set_order_status,
    set_product_active,
    set_product_photo,
    set_user_language,
    update_category,
    update_product,
    upsert_user,
)
from keyboards import (
    admin_back_keyboard,
    admin_cancel_keyboard,
    admin_categories_keyboard,
    admin_category_delete_keyboard,
    admin_category_keyboard,
    admin_main_keyboard,
    admin_new_order_keyboard,
    admin_order_keyboard,
    admin_orders_keyboard,
    admin_payment_keyboard,
    admin_payments_keyboard,
    admin_product_cancel_keyboard,
    admin_product_categories_keyboard,
    admin_product_delete_keyboard,
    admin_product_keyboard,
    admin_products_keyboard,
    admin_user_keyboard,
    admin_user_order_keyboard,
    admin_user_orders_keyboard,
    admin_users_keyboard,
    cart_keyboard,
    categories_keyboard,
    contact_keyboard,
    delivery_keyboard,
    language_keyboard,
    main_keyboard,
    order_confirmation_keyboard,
    payment_check_keyboard,
    payment_keyboard,
    product_keyboard,
    products_keyboard,
    remove_keyboard,
)
from states import (
    AdminCategoryCreateState,
    AdminCategoryEditState,
    AdminProductCreateState,
    AdminProductEditState,
    AdminProductPhotoState,
    CheckoutState,
)
from texts import localized_value, text


dp = Dispatcher()
PICKUP_ADDRESS = "Myslíkova 6, 110 00 Nové Město"
PICKUP_HOURS = "Пн–Пт: 10:00–18:00"

# ----------------------------------------------------------------------
# Общие функции
# ----------------------------------------------------------------------


def is_admin(user_id: int) -> bool:
    return int(user_id) == settings.admin_id


async def require_admin_callback(
    callback: CallbackQuery,
) -> bool:
    if is_admin(callback.from_user.id):
        return True

    await callback.answer(
        "Нет доступа",
        show_alert=True,
    )
    return False


async def require_admin_message(
    message: Message,
    state: FSMContext | None = None,
) -> bool:
    if (
        message.from_user is not None
        and is_admin(message.from_user.id)
    ):
        return True

    if state is not None:
        await state.clear()

    await message.answer("Нет доступа.")
    return False


def user_language(user_id: int) -> str:
    return get_user_language(user_id)


def register_telegram_user(
    message: Message,
) -> str:
    user = message.from_user

    if user is None:
        return "ru"

    saved_user = get_user(user.id)

    if saved_user is None:
        language = (
            user.language_code
            if user.language_code in SUPPORTED_LANGUAGES
            else "ru"
        )
    else:
        language = get_user_language(user.id)

    upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=language,
    )

    return language


def valid_name(value: str) -> bool:
    value = " ".join(str(value or "").strip().split())

    return (
        2 <= len(value) <= 80
        and re.fullmatch(
            r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*",
            value,
            flags=re.UNICODE,
        )
        is not None
    )


def valid_phone(value: str) -> bool:
    digits = re.sub(
        r"\D",
        "",
        str(value or "").strip(),
    )
    return 7 <= len(digits) <= 15


def valid_address(value: str) -> bool:
    value = " ".join(str(value or "").strip().split())

    return (
        5 <= len(value) <= 200
        and re.search(
            r"[\w\u00C0-\u024F\u0400-\u04FF]",
            value,
            flags=re.UNICODE,
        )
        is not None
    )


def delivery_name(
    delivery_method: str,
    language: str,
) -> str:
    key = {
        "zasilkovna": "delivery_zasilkovna",
        "dhl": "delivery_dhl",
        "pickup": "delivery_pickup",
    }.get(delivery_method)

    return (
        text(language, key)
        if key
        else delivery_method
    )


def payment_name(
    payment_method: str,
    language: str,
) -> str:
    key = {
        "cash": "payment_cash",
        "qr": "payment_qr",
    }.get(payment_method)

    return (
        text(language, key)
        if key
        else payment_method
    )


def status_name(
    value: str,
    language: str,
) -> str:
    values = {
        "ru": {
            "new": "Новый",
            "accepted": "Принят",
            "packed": "Упакован",
            "shipped": "Отправлен",
            "completed": "Завершён",
            "cancelled": "Отменён",
            "pending": "Ожидается",
            "checking": "Проверяется",
            "paid": "Оплачено",
            "rejected": "Отклонено",
        },
        "cs": {
            "new": "Nová",
            "accepted": "Přijata",
            "packed": "Zabalena",
            "shipped": "Odeslána",
            "completed": "Dokončena",
            "cancelled": "Zrušena",
            "pending": "Čeká",
            "checking": "Kontroluje se",
            "paid": "Zaplaceno",
            "rejected": "Zamítnuto",
        },
        "uk": {
            "new": "Нове",
            "accepted": "Прийняте",
            "packed": "Запаковане",
            "shipped": "Відправлене",
            "completed": "Завершене",
            "cancelled": "Скасоване",
            "pending": "Очікується",
            "checking": "Перевіряється",
            "paid": "Оплачено",
            "rejected": "Відхилено",
        },
    }

    return values.get(
        language,
        values["ru"],
    ).get(value, value)


def format_product(
    product: Any,
    language: str,
) -> str:
    name = localized_value(
        product,
        "name",
        language,
    )
    description = localized_value(
        product,
        "description",
        language,
    )

    lines = [
        f"🧴 <b>{escape(name)}</b>",
        "",
    ]

    if description:
        lines.extend(
            [
                escape(description),
                "",
            ]
        )

    lines.append(
        text(
            language,
            "product_price",
            price=int(product["price"]),
            currency=settings.currency,
        )
    )

    return "\n".join(lines)


def format_cart(
    user_id: int,
    language: str,
) -> tuple[str, int]:
    cart = get_cart(user_id)

    if not cart:
        return text(language, "cart_empty"), 0

    lines = [
        text(language, "cart_title"),
        "",
    ]
    total = 0

    for item in cart:
        quantity = int(item["quantity"])
        price = int(item["price"])
        subtotal = price * quantity
        total += subtotal

        lines.append(
            text(
                language,
                "cart_item",
                name=escape(
                    localized_value(
                        item,
                        "name",
                        language,
                    )
                ),
                quantity=quantity,
                price=price,
                subtotal=subtotal,
                currency=settings.currency,
            )
        )
        lines.append("")

    lines.append(
        text(
            language,
            "cart_total",
            total=total,
            currency=settings.currency,
        )
    )

    return "\n".join(lines), total


def calculate_cart_total(
    user_id: int,
) -> int:
    return sum(
        int(item["price"])
        * int(item["quantity"])
        for item in get_cart(user_id)
    )


def resolve_product_photo(
    photo: str,
) -> str | FSInputFile:
    photo = str(photo or "").strip()

    if photo.startswith(
        ("http://", "https://")
    ):
        return photo

    photo_path = settings.images_dir / photo

    if photo_path.is_file():
        return FSInputFile(photo_path)

    return photo


async def replace_message(
    message: Message,
    value: str,
    reply_markup=None,
) -> None:
    if message.photo:
        try:
            await message.delete()
        except Exception:
            pass

        await message.answer(
            value,
            reply_markup=reply_markup,
        )
        return

    try:
        await message.edit_text(
            value,
            reply_markup=reply_markup,
        )
    except Exception:
        await message.answer(
            value,
            reply_markup=reply_markup,
        )


def create_payment_qr(
    order: Any,
) -> BufferedInputFile | None:
    iban = re.sub(
        r"\s+",
        "",
        str(settings.payment_iban or ""),
    ).upper()

    if not iban:
        return None

    order_id = int(order["id"])
    total = int(order["total"])
    currency = str(
        order["currency"] or settings.currency
    ).upper()

    variable_symbol = str(
        order["variable_symbol"] or order_id
    )

    message = f"Order {order_id}"

    # Чешский формат QR Platba — Short Payment Descriptor.
    payload = "*".join(
        [
            "SPD",
            "1.0",
            f"ACC:{iban}",
            f"AM:{total:.2f}",
            f"CC:{currency}",
            f"X-VS:{variable_symbol}",
            f"MSG:{message}",
        ]
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=(
            qrcode.constants.ERROR_CORRECT_M
        ),
        box_size=10,
        border=4,
    )

    qr.add_data(payload)
    qr.make(fit=True)

    image = qr.make_image(
        fill_color="black",
        back_color="white",
    )

    buffer = BytesIO()
    image.save(buffer, format="PNG")

    return BufferedInputFile(
        file=buffer.getvalue(),
        filename=f"payment_{order_id}.png",
    )


def payment_instructions(
    order: Any,
    language: str,
) -> str:
    if not settings.payment_iban:
        return text(
            language,
            "payment_qr_not_configured",
        )

    return text(
        language,
        "payment_qr_instructions",
        order_id=int(order["id"]),
        recipient=escape(
            settings.payment_recipient
        ),
        iban=escape(settings.payment_iban),
        total=int(order["total"]),
        currency=escape(
            str(order["currency"])
        ),
        variable_symbol=escape(
            str(
                order["variable_symbol"]
                or order["id"]
            )
        ),
    )


ORDER_STATUS_NAMES = {
    "new": "🆕 Новый",
    "accepted": "✅ Принят",
    "packed": "📦 Упакован",
    "shipped": "🚚 Отправлен",
    "completed": "🏁 Завершён",
    "cancelled": "❌ Отменён",
}

PAYMENT_STATUS_NAMES = {
    "pending": "⏳ Ожидает оплаты",
    "checking": "🔎 На проверке",
    "paid": "✅ Оплачено",
    "rejected": "❌ Отклонено",
}


def format_admin_order(
    order: Any,
    items: list[Any],
) -> str:
    status = ORDER_STATUS_NAMES.get(
        str(order["status"]),
        escape(str(order["status"])),
    )
    payment_status = PAYMENT_STATUS_NAMES.get(
        str(order["payment_status"]),
        escape(str(order["payment_status"])),
    )
    currency = escape(
        str(order["currency"])
    )

    lines = [
        f"📦 <b>Заказ #{int(order['id'])}</b>",
        "",
        f"Статус: {status}",
        (
            "Способ оплаты: "
            f"{escape(payment_name(str(order['payment_method']), 'ru'))}"
        ),
        f"Статус оплаты: {payment_status}",
        "",
        f"👤 {escape(str(order['customer_name']))}",
        f"📞 {escape(str(order['phone']))}",
        f"📍 {escape(str(order['address']))}",
        (
            "Доставка: "
            f"{escape(delivery_name(str(order['delivery_method']), 'ru'))}"
        ),
        "",
        "<b>Товары:</b>",
    ]

    for item in items:
        quantity = int(item["quantity"])
        price = int(item["price"])

        lines.append(
            f"• {escape(str(item['product_name']))} "
            f"× {quantity} = "
            f"{price * quantity} {currency}"
        )

    lines.extend(
        [
            "",
            (
                f"Товары: {int(order['products_total'])} "
                f"{currency}"
            ),
            (
                f"Доставка: {int(order['delivery_price'])} "
                f"{currency}"
            ),
            (
                f"<b>Итого: {int(order['total'])} "
                f"{currency}</b>"
            ),
            (
                "Дата: "
                f"{escape(str(order['created_at']))}"
            ),
        ]
    )

    if order["variable_symbol"]:
        lines.append(
            "VS: "
            f"<code>{escape(str(order['variable_symbol']))}</code>"
        )

    return "\n".join(lines)


def format_admin_order_by_id(
    order_id: int,
) -> str | None:
    order = get_order(order_id)

    if order is None:
        return None

    return format_admin_order(
        order,
        get_order_items(order_id),
    )


async def show_main_menu(
    message: Message,
    language: str,
) -> None:
    await message.answer(
        text(language, "welcome"),
        reply_markup=main_keyboard(language),
    )


async def show_categories(
    message: Message,
    language: str,
) -> None:
    categories = get_categories(
        active_only=True
    )

    if not categories:
        await message.answer(
            text(language, "catalog_empty"),
            reply_markup=main_keyboard(language),
        )
        return

    await message.answer(
        text(language, "categories_title"),
        reply_markup=categories_keyboard(
            categories,
            language,
        ),
    )


async def show_cart(
    message: Message,
    user_id: int,
    language: str,
) -> None:
    cart = get_cart(user_id)
    cart_text, _ = format_cart(
        user_id,
        language,
    )

    await message.answer(
        cart_text,
        reply_markup=(
            cart_keyboard(cart, language)
            if cart
            else main_keyboard(language)
        ),
    )


async def refresh_cart_callback(
    callback: CallbackQuery,
    language: str,
) -> None:
    if callback.message is None:
        return

    cart = get_cart(callback.from_user.id)
    cart_text, _ = format_cart(
        callback.from_user.id,
        language,
    )

    if not cart:
        await replace_message(
            callback.message,
            cart_text,
        )
        await callback.message.answer(
            text(language, "main_menu"),
            reply_markup=main_keyboard(language),
        )
        return

    await replace_message(
        callback.message,
        cart_text,
        cart_keyboard(cart, language),
    )


# ----------------------------------------------------------------------
# Запуск, язык и главное меню
# ----------------------------------------------------------------------

@dp.message(CommandStart())
async def start_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    await message.answer(
        text(language, "language_title"),
        reply_markup=language_keyboard(),
    )


@dp.callback_query(F.data.startswith("lang:"))
async def language_callback(
    callback: CallbackQuery,
) -> None:
    try:
        language = str(
            callback.data
        ).split(":", 1)[1]
    except IndexError:
        language = "ru"

    if language not in SUPPORTED_LANGUAGES:
        await callback.answer(
            "Unknown language",
            show_alert=True,
        )
        return

    user = callback.from_user

    upsert_user(
        user_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language=language,
    )
    set_user_language(
        user.id,
        language,
    )

    await callback.answer(
        text(language, "language_saved")
    )

    if callback.message:
        await replace_message(
            callback.message,
            text(language, "language_saved"),
        )
        await show_main_menu(
            callback.message,
            language,
        )


@dp.message(Command("language"))
async def language_command(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    await message.answer(
        text(language, "language_title"),
        reply_markup=language_keyboard(),
    )


@dp.message(Command("menu"))
async def menu_command(
    message: Message,
) -> None:
    language = register_telegram_user(message)
    await show_main_menu(message, language)


@dp.callback_query(F.data == "main:back")
async def main_back_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    await callback.answer()

    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await show_main_menu(
            callback.message,
            language,
        )


@dp.message(
    F.text.in_(
        [
            text("ru", "language"),
            text("cs", "language"),
            text("uk", "language"),
        ]
    )
)
async def language_menu_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    await message.answer(
        text(language, "language_title"),
        reply_markup=language_keyboard(),
    )


@dp.message(
    F.text.in_(
        [
            text("ru", "contacts"),
            text("cs", "contacts"),
            text("uk", "contacts"),
        ]
    )
)
async def contacts_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    await message.answer(
        text(language, "contacts_text"),
        reply_markup=main_keyboard(language),
    )


# ----------------------------------------------------------------------
# Каталог
# ----------------------------------------------------------------------

@dp.message(
    F.text.in_(
        [
            text("ru", "catalog"),
            text("cs", "catalog"),
            text("uk", "catalog"),
        ]
    )
)
async def catalog_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)
    await show_categories(message, language)


@dp.callback_query(
    F.data == "catalog:categories"
)
async def categories_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    categories = get_categories(
        active_only=True
    )

    await callback.answer()

    if callback.message is None:
        return

    await replace_message(
        callback.message,
        (
            text(language, "categories_title")
            if categories
            else text(language, "catalog_empty")
        ),
        (
            categories_keyboard(
                categories,
                language,
            )
            if categories
            else None
        ),
    )


@dp.callback_query(
    F.data.regexp(r"^category:\d+$")
)
async def category_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    category_id = int(
        str(callback.data).split(":")[1]
    )
    category = get_category(category_id)

    if (
        category is None
        or not bool(category["is_active"])
    ):
        await callback.answer(
            text(language, "catalog_empty"),
            show_alert=True,
        )
        return

    products = get_products(
        category_id=category_id,
        active_only=True,
    )
    category_name = localized_value(
        category,
        "name",
        language,
    )

    await callback.answer()

    if callback.message is None:
        return

    value = f"🧴 <b>{escape(category_name)}</b>"

    if not products:
        value += (
            "\n\n"
            + text(language, "category_empty")
        )

    await replace_message(
        callback.message,
        value,
        products_keyboard(
            products,
            language,
        ),
    )


@dp.callback_query(
    F.data.regexp(r"^product:\d+$")
)
async def product_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    product_id = int(
        str(callback.data).split(":")[1]
    )
    product = get_product(product_id)

    if (
        product is None
        or not bool(product["is_active"])
    ):
        await callback.answer(
            text(language, "catalog_empty"),
            show_alert=True,
        )
        return

    caption = format_product(
        product,
        language,
    )
    markup = product_keyboard(
        product_id=product_id,
        category_id=int(
            product["category_id"]
        ),
        language=language,
        in_stock=True,
    )

    await callback.answer()

    if callback.message is None:
        return

    photo = str(
        product["photo"] or ""
    ).strip()

    if photo:
        try:
            try:
                await callback.message.delete()
            except Exception:
                pass

            await callback.message.answer_photo(
                photo=resolve_product_photo(photo),
                caption=caption,
                reply_markup=markup,
            )
            return
        except Exception as error:
            logging.warning(
                "Не удалось отправить фото "
                "товара %s: %s",
                product_id,
                error,
            )

    await replace_message(
        callback.message,
        caption,
        markup,
    )


# ----------------------------------------------------------------------
# Корзина
# ----------------------------------------------------------------------

@dp.message(
    F.text.in_(
        [
            text("ru", "cart"),
            text("cs", "cart"),
            text("uk", "cart"),
        ]
    )
)
async def cart_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    if message.from_user:
        await show_cart(
            message,
            message.from_user.id,
            language,
        )


@dp.callback_query(
    F.data.regexp(r"^cart:add:\d+$")
)
async def add_to_cart_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    product_id = int(
        str(callback.data).split(":")[2]
    )

    success = add_to_cart(
        callback.from_user.id,
        product_id,
        1,
    )

    await callback.answer(
        text(
            language,
            (
                "added_to_cart"
                if success
                else "add_failed"
            ),
        ),
        show_alert=not success,
    )


@dp.callback_query(
    F.data.regexp(r"^cart:plus:\d+$")
)
async def cart_plus_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    product_id = int(
        str(callback.data).split(":")[2]
    )

    item = next(
        (
            row
            for row in get_cart(
                callback.from_user.id
            )
            if int(row["product_id"])
            == product_id
        ),
        None,
    )

    if item is None:
        await callback.answer(
            text(language, "cart_empty"),
            show_alert=True,
        )
        return

    success = set_cart_quantity(
        callback.from_user.id,
        product_id,
        int(item["quantity"]) + 1,
    )

    if not success:
        await callback.answer(
            text(language, "add_failed"),
            show_alert=True,
        )
        return

    await callback.answer(
        text(language, "quantity_changed")
    )
    await refresh_cart_callback(
        callback,
        language,
    )


@dp.callback_query(
    F.data.regexp(r"^cart:minus:\d+$")
)
async def cart_minus_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    product_id = int(
        str(callback.data).split(":")[2]
    )

    item = next(
        (
            row
            for row in get_cart(
                callback.from_user.id
            )
            if int(row["product_id"])
            == product_id
        ),
        None,
    )

    if item is None:
        await callback.answer(
            text(language, "cart_empty"),
            show_alert=True,
        )
        return

    success = set_cart_quantity(
        callback.from_user.id,
        product_id,
        int(item["quantity"]) - 1,
    )

    if not success:
        await callback.answer(
            text(language, "add_failed"),
            show_alert=True,
        )
        return

    await callback.answer(
        text(language, "quantity_changed")
    )
    await refresh_cart_callback(
        callback,
        language,
    )


@dp.callback_query(F.data == "cart:clear")
async def clear_cart_callback(
    callback: CallbackQuery,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    clear_cart(callback.from_user.id)

    await callback.answer(
        text(language, "cart_cleared")
    )

    if callback.message:
        await replace_message(
            callback.message,
            text(language, "cart_empty"),
        )
        await callback.message.answer(
            text(language, "main_menu"),
            reply_markup=main_keyboard(language),
        )


@dp.callback_query(F.data == "noop")
async def noop_callback(
    callback: CallbackQuery,
) -> None:
    await callback.answer()


# ----------------------------------------------------------------------
# Мои заказы
# ----------------------------------------------------------------------

@dp.message(
    F.text.in_(
        [
            text("ru", "orders"),
            text("cs", "orders"),
            text("uk", "orders"),
        ]
    )
)
async def orders_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    if message.from_user is None:
        return

    orders = get_user_orders(
        message.from_user.id,
        limit=10,
    )

    if not orders:
        await message.answer(
            text(language, "my_orders_empty"),
            reply_markup=main_keyboard(language),
        )
        return

    lines: list[str] = []

    for order in orders:
        lines.extend(
            [
                text(
                    language,
                    "order_summary",
                    order_id=int(order["id"]),
                    total=int(order["total"]),
                    currency=escape(
                        str(order["currency"])
                    ),
                    status=status_name(
                        str(order["status"]),
                        language,
                    ),
                    payment_status=status_name(
                        str(
                            order[
                                "payment_status"
                            ]
                        ),
                        language,
                    ),
                ),
                "",
            ]
        )

    await message.answer(
        "\n".join(lines),
        reply_markup=main_keyboard(language),
    )


# ----------------------------------------------------------------------
# Оформление заказа
# ----------------------------------------------------------------------

@dp.callback_query(F.data == "checkout:start")
async def checkout_start_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language = user_language(
        callback.from_user.id
    )

    if not get_cart(callback.from_user.id):
        await callback.answer(
            text(language, "cart_empty"),
            show_alert=True,
        )
        return

    await state.clear()
    await state.set_state(
        CheckoutState.name
    )
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            text(language, "checkout_name"),
            reply_markup=remove_keyboard(),
        )


@dp.message(CheckoutState.name)
async def checkout_name_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language = register_telegram_user(message)
    customer_name = " ".join(
        (message.text or "").strip().split()
    )

    if customer_name == text(
        language,
        "cancel",
    ):
        await state.clear()
        await message.answer(
            text(language, "checkout_cancelled"),
            reply_markup=main_keyboard(language),
        )
        return

    if not valid_name(customer_name):
        await message.answer(
            text(language, "invalid_name")
        )
        return

    await state.update_data(
        customer_name=customer_name
    )
    await state.set_state(
        CheckoutState.phone
    )

    await message.answer(
        text(language, "checkout_phone"),
        reply_markup=contact_keyboard(language),
    )


@dp.message(CheckoutState.phone)
async def checkout_phone_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language = register_telegram_user(message)

    if message.text == text(
        language,
        "cancel",
    ):
        await state.clear()
        await message.answer(
            text(language, "checkout_cancelled"),
            reply_markup=main_keyboard(language),
        )
        return

    contact = message.contact

    if contact is None:
        await message.answer(
            text(language, "invalid_phone"),
            reply_markup=contact_keyboard(language),
        )
        return

    if (
        message.from_user is None
        or (
            contact.user_id is not None
            and contact.user_id
            != message.from_user.id
        )
    ):
        await message.answer(
            text(language, "invalid_phone"),
            reply_markup=contact_keyboard(language),
        )
        return

    phone = str(
        contact.phone_number or ""
    ).strip()

    if not valid_phone(phone):
        await message.answer(
            text(language, "invalid_phone"),
            reply_markup=contact_keyboard(language),
        )
        return

    await state.update_data(phone=phone)
    await state.set_state(
        CheckoutState.delivery
    )

    await message.answer(
        text(language, "choose_delivery"),
        reply_markup=delivery_keyboard(language),
    )


@dp.callback_query(
    CheckoutState.delivery,
    F.data.startswith("checkout:delivery:"),
)
async def checkout_delivery_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language = user_language(
        callback.from_user.id
    )

    delivery_method = str(
        callback.data
    ).split(":")[2]

    if delivery_method not in DELIVERY_METHODS:
        await callback.answer(
            "Invalid delivery",
            show_alert=True,
        )
        return

    await state.update_data(
        delivery_method=delivery_method,
        delivery_price=int(
            DELIVERY_METHODS[delivery_method]
        ),
    )

    await callback.answer()

    if callback.message is None:
        return

    # Удаляем сообщение с кнопками доставки.
    try:
        await callback.message.delete()
    except Exception:
        try:
            await callback.message.edit_reply_markup(
                reply_markup=None
            )
        except Exception:
            pass

    if delivery_method == "pickup":
        pickup_details = (
            f"{PICKUP_ADDRESS}; {PICKUP_HOURS}"
        )

        await state.update_data(
            address=pickup_details
        )
        await state.set_state(
            CheckoutState.payment
        )

        # Убирает кнопку «Поделиться номером».
        await callback.message.answer(
            text(
                language,
                "pickup_info",
                address=escape(PICKUP_ADDRESS),
                hours=escape(PICKUP_HOURS),
            ),
            reply_markup=remove_keyboard(),
        )

        await callback.message.answer(
            text(language, "choose_payment"),
            reply_markup=payment_keyboard(language),
        )
        return

    # Zásilkovna или DHL.
    await state.set_state(
        CheckoutState.address
    )

    # ReplyKeyboardRemove скрывает кнопку отправки номера.
    await callback.message.answer(
        text(language, "checkout_address"),
        reply_markup=remove_keyboard(),
    )


@dp.message(CheckoutState.address)
async def checkout_address_handler(
    message: Message,
    state: FSMContext,
) -> None:
    language = register_telegram_user(message)
    address = " ".join(
        (message.text or "").strip().split()
    )

    if address == text(
        language,
        "cancel",
    ):
        await state.clear()
        await message.answer(
            text(language, "checkout_cancelled"),
            reply_markup=main_keyboard(language),
        )
        return

    if not valid_address(address):
        await message.answer(
            text(language, "invalid_address")
        )
        return

    await state.update_data(address=address)
    await state.set_state(
        CheckoutState.payment
    )

    await message.answer(
        text(language, "choose_payment"),
        reply_markup=payment_keyboard(language),
    )


@dp.callback_query(
    CheckoutState.payment,
    F.data == "checkout:back:delivery",
)
async def checkout_back_to_delivery(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language = user_language(
        callback.from_user.id
    )

    # Удаляем ранее выбранный способ доставки.
    # Имя, телефон и другие данные клиента сохраняются.
    await state.update_data(
        delivery_method=None,
        delivery_price=0,
        address=None,
        payment_method=None,
    )

    # Возвращаем пользователя на этап выбора доставки.
    await state.set_state(
        CheckoutState.delivery
    )

    # Закрываем индикатор загрузки Telegram.
    await callback.answer()

    if callback.message is None:
        return

    try:
        # Заменяем сообщение выбора оплаты
        # сообщением выбора доставки.
        await callback.message.edit_text(
            text(language, "choose_delivery"),
            reply_markup=delivery_keyboard(language),
        )
    except Exception:
        # Если старое сообщение невозможно изменить,
        # отправляем новое.
        await callback.message.answer(
            text(language, "choose_delivery"),
            reply_markup=delivery_keyboard(language),
        )


@dp.callback_query(
    CheckoutState.payment,
    F.data.startswith("checkout:payment:"),
)
async def checkout_payment_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    payment_method = str(
        callback.data
    ).split(":")[2]

    if payment_method not in PAYMENT_METHODS:
        await callback.answer(
            "Invalid payment",
            show_alert=True,
        )
        return

    if not get_cart(callback.from_user.id):
        await state.clear()
        await callback.answer(
            text(language, "cart_empty"),
            show_alert=True,
        )
        return

    await state.update_data(
        payment_method=payment_method
    )
    data = await state.get_data()

    required = {
        "customer_name",
        "phone",
        "address",
        "delivery_method",
        "delivery_price",
    }

    if not required.issubset(data):
        await state.clear()
        await callback.answer(
            text(language, "checkout_data_lost"),
            show_alert=True,
        )
        return

    products_total = calculate_cart_total(
        callback.from_user.id
    )
    delivery_price = int(
        data["delivery_price"]
    )
    total = products_total + delivery_price

    summary = text(
        language,
        "confirm_order",
        name=escape(
            str(data["customer_name"])
        ),
        phone=escape(str(data["phone"])),
        address=escape(
            str(data["address"])
        ),
        delivery=escape(
            delivery_name(
                str(data["delivery_method"]),
                language,
            )
        ),
        payment=escape(
            payment_name(
                payment_method,
                language,
            )
        ),
        products_total=products_total,
        delivery_price=delivery_price,
        total=total,
        currency=settings.currency,
    )

    await state.set_state(
        CheckoutState.confirmation
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            summary,
            order_confirmation_keyboard(
                language
            ),
        )


@dp.callback_query(
    CheckoutState.confirmation,
    F.data == "checkout:confirm",
)
async def checkout_confirm_handler(
    callback: CallbackQuery,
    state: FSMContext,
    bot: Bot,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    data = await state.get_data()

    required = {
        "customer_name",
        "phone",
        "address",
        "delivery_method",
        "delivery_price",
        "payment_method",
    }

    if not required.issubset(data):
        await state.clear()
        await callback.answer(
            text(language, "checkout_data_lost"),
            show_alert=True,
        )
        return

    try:
        order_id = create_order(
            user_id=callback.from_user.id,
            customer_name=str(
                data["customer_name"]
            ),
            phone=str(data["phone"]),
            address=str(data["address"]),
            delivery_method=str(
                data["delivery_method"]
            ),
            delivery_price=int(
                data["delivery_price"]
            ),
            language=language,
            payment_method=str(
                data["payment_method"]
            ),
        )
    except ValueError:
        await callback.answer(
            text(language, "cart_changed"),
            show_alert=True,
        )
        return
    except Exception:
        logging.exception(
            "Ошибка создания заказа"
        )
        await callback.answer(
            text(language, "order_failed"),
            show_alert=True,
        )
        return

    if order_id is None:
        await callback.answer(
            text(language, "cart_empty"),
            show_alert=True,
        )
        return

    order = get_order(order_id)

    if order is None:
        await state.clear()
        await callback.answer(
            text(language, "order_failed"),
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            text(
                language,
                "order_created",
                order_id=order_id,
                total=int(order["total"]),
                currency=escape(
                    str(order["currency"])
                ),
            ),
        )

        if str(order["payment_method"]) == "qr":
            markup = (
                payment_check_keyboard(
                    order_id,
                    language,
                )
                if settings.payment_iban
                else None
            )

            instructions = payment_instructions(
                order,
                language,
            )

            try:
                qr_file = create_payment_qr(order)

                if qr_file is not None:
                    await callback.message.answer_photo(
                        photo=qr_file,
                        caption=instructions,
                        reply_markup=markup,
                    )
                else:
                    await callback.message.answer(
                        instructions,
                        reply_markup=markup,
                    )

            except Exception:
                logging.exception(
                    "Ошибка генерации или отправки QR-кода "
                    "для заказа %s",
                    order_id,
                )

                await callback.message.answer(
                    instructions,
                    reply_markup=markup,
                )

        await callback.message.answer(
            text(language, "main_menu"),
            reply_markup=main_keyboard(language),
        )

    admin_text = format_admin_order_by_id(
        order_id
    )

    if admin_text:
        try:
            await bot.send_message(
                settings.admin_id,
                admin_text,
                reply_markup=(
                    admin_new_order_keyboard(
                        order_id,
                        str(order["payment_method"]),
                    )
                ),
            )
        except Exception as error:
            logging.warning(
                "Администратор не получил "
                "уведомление: %s",
                error,
            )


@dp.callback_query(
    F.data == "checkout:cancel"
)
async def checkout_cancel_handler(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    await state.clear()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            text(language, "checkout_cancelled"),
        )
        await callback.message.answer(
            text(language, "main_menu"),
            reply_markup=main_keyboard(language),
        )


@dp.callback_query(
    F.data.regexp(r"^payment:check:\d+$")
)
async def payment_check_handler(
    callback: CallbackQuery,
    bot: Bot,
) -> None:
    language = user_language(
        callback.from_user.id
    )
    order_id = int(
        str(callback.data).split(":")[2]
    )

    requested = request_payment_check(
        order_id,
        callback.from_user.id,
    )

    if not requested:
        await callback.answer(
            text(
                language,
                "payment_check_failed",
            ),
            show_alert=True,
        )
        return

    await callback.answer(
        text(
            language,
            "payment_check_requested",
        ),
        show_alert=True,
    )

    order_text = format_admin_order_by_id(
        order_id
    )

    if order_text:
        try:
            await bot.send_message(
                settings.admin_id,
                (
                    "💳 <b>Клиент сообщил "
                    "об оплате</b>\n\n"
                    f"{order_text}"
                ),
                reply_markup=(
                    admin_new_order_keyboard(
                        order_id,
                        "qr",
                    )
                ),
            )
        except Exception as error:
            logging.warning(
                "Ошибка уведомления "
                "об оплате: %s",
                error,
            )


# ----------------------------------------------------------------------
# Администратор — общие экраны
# ----------------------------------------------------------------------

async def show_admin_categories(
    message: Message,
) -> None:
    await replace_message(
        message,
        (
            "🗂 <b>Управление категориями</b>\n\n"
            "✅ — видна клиентам\n"
            "🚫 — скрыта"
        ),
        admin_categories_keyboard(
            get_categories(active_only=False)
        ),
    )


async def show_admin_category(
    message: Message,
    category_id: int,
) -> None:
    category = get_category(category_id)

    if category is None:
        await replace_message(
            message,
            "Категория не найдена.",
            admin_back_keyboard(),
        )
        return

    status = (
        "✅ Показывается"
        if bool(category["is_active"])
        else "🚫 Скрыта"
    )

    await replace_message(
        message,
        (
            "🗂 <b>Категория</b>\n\n"
            f"ID: <code>{int(category['id'])}</code>\n"
            f"🇷🇺 {escape(str(category['name_ru']))}\n"
            f"🇨🇿 {escape(str(category['name_cs']))}\n"
            f"🇺🇦 {escape(str(category['name_uk']))}\n"
            f"Порядок: {int(category['sort_order'])}\n"
            f"Статус: {status}"
        ),
        admin_category_keyboard(
            int(category["id"]),
            bool(category["is_active"]),
        ),
    )


async def show_admin_products(
    message: Message,
) -> None:
    await replace_message(
        message,
        (
            "🧴 <b>Управление товарами</b>\n\n"
            "✅ — показывается\n"
            "🚫 — скрыт"
        ),
        admin_products_keyboard(
            get_products(active_only=False)
        ),
    )


async def show_admin_product(
    message: Message,
    product_id: int,
) -> None:
    product = get_product(product_id)

    if product is None:
        await replace_message(
            message,
            "Товар не найден.",
            admin_back_keyboard(),
        )
        return

    category = get_category(
        int(product["category_id"])
    )
    category_name = (
        str(category["name_ru"])
        if category
        else "Категория удалена"
    )
    status = (
        "✅ Показывается"
        if bool(product["is_active"])
        else "🚫 Скрыт"
    )

    product_text = (
        "🧴 <b>Товар</b>\n\n"
        f"ID: <code>{int(product['id'])}</code>\n"
        f"Категория: {escape(category_name)}\n"
        f"🇷🇺 {escape(str(product['name_ru']))}\n"
        f"🇨🇿 {escape(str(product['name_cs']))}\n"
        f"🇺🇦 {escape(str(product['name_uk']))}\n\n"
        f"{escape(str(product['description_ru'] or ''))}\n\n"
        f"Цена: <b>{int(product['price'])} "
        f"{settings.currency}</b>\n"

        f"Статус: {status}"
    )
    markup = admin_product_keyboard(
        int(product["id"]),
        bool(product["is_active"]),
    )
    photo = str(
        product["photo"] or ""
    ).strip()

    try:
        await message.delete()
    except Exception:
        pass

    if photo:
        try:
            await message.answer_photo(
                photo=resolve_product_photo(photo),
                caption=product_text,
                reply_markup=markup,
            )
            return
        except Exception as error:
            logging.warning(
                "Ошибка отправки фото товара: %s",
                error,
            )

    await message.answer(
        product_text,
        reply_markup=markup,
    )


async def ask_product_field(
    message: Message,
    state: FSMContext,
    next_state,
    data_key: str,
    value: str,
    prompt: str,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = value.strip()

    if not value:
        await message.answer(
            "Поле не может быть пустым.",
            reply_markup=(
                admin_product_cancel_keyboard()
            ),
        )
        return

    await state.update_data(
        **{data_key: value}
    )
    await state.set_state(next_state)
    await message.answer(
        prompt,
        reply_markup=(
            admin_product_cancel_keyboard()
        ),
    )


@dp.message(Command("admin"))
async def admin_handler(
    message: Message,
) -> None:
    if (
        message.from_user is None
        or not is_admin(message.from_user.id)
    ):
        language = (
            user_language(message.from_user.id)
            if message.from_user
            else "ru"
        )
        await message.answer(
            text(language, "admin_only")
        )
        return

    # Полностью скрываем нижнее клиентское меню.
    hide_message = await message.answer(
        "⚙️ Открываю админ-панель…",
        reply_markup=remove_keyboard(),
    )

    try:
        await hide_message.delete()
    except Exception:
        pass

    await message.answer(
        "⚙️ <b>Админ-панель Beauty Shop</b>",
        reply_markup=admin_main_keyboard(),
    )


@dp.callback_query(F.data == "admin:main")
async def admin_main_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            "⚙️ <b>Админ-панель Beauty Shop</b>",
            admin_main_keyboard(),
        )


# ----------------------------------------------------------------------
# Администратор — пользователи и статистика
# ----------------------------------------------------------------------

async def show_admin_users(
    callback: CallbackQuery,
    page: int,
) -> None:
    page_size = 10
    total = count_users()

    if total == 0:
        page = 0
    else:
        max_page = (total - 1) // page_size
        page = min(max(0, page), max_page)

    users = get_users(
        limit=page_size,
        offset=page * page_size,
    )

    value = (
        "👥 <b>Пользователи бота</b>\n"
        f"Всего: <b>{total}</b>\n\n"
        "Выберите пользователя:"
        if users
        else (
            "👥 <b>Пользователи бота</b>\n\n"
            "Пользователей пока нет."
        )
    )

    if callback.message:
        await replace_message(
            callback.message,
            value,
            admin_users_keyboard(
                page=page,
                total=total,
                page_size=page_size,
                users=users,
            ),
        )


@dp.callback_query(
    F.data.regexp(r"^admin:users:\d+$")
)
async def admin_users_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    page = int(
        str(callback.data).split(":")[2]
    )
    await callback.answer()
    await show_admin_users(callback, page)


@dp.callback_query(F.data == "admin:stats")
async def admin_stats_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    stats = get_statistics()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "📊 <b>Статистика магазина</b>\n\n"
                "👥 Всего пользователей: "
                f"<b>{stats['users_total']}</b>\n"
                "🆕 За последние 24 часа: "
                f"<b>{stats['users_today']}</b>\n"
                "📅 За последние 7 дней: "
                f"<b>{stats['users_week']}</b>\n\n"
                "📦 Всего заказов: "
                f"<b>{stats['orders_total']}</b>\n"
                "🔔 Новых заказов: "
                f"<b>{stats['orders_new']}</b>\n"
                "💰 Сумма заказов: "
                f"<b>{stats['revenue']} "
                f"{settings.currency}</b>"
            ),
            admin_back_keyboard(),
        )


@dp.callback_query(
    F.data.regexp(r"^admin:user:\d+$")
)
async def admin_user_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    user_id = int(
        str(callback.data).split(":")[2]
    )
    user = get_user(user_id)

    if user is None:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return

    username = (
        f"@{escape(str(user['username']))}"
        if user["username"]
        else "не указан"
    )
    full_name = " ".join(
        value
        for value in (
            str(user["first_name"] or "").strip(),
            str(user["last_name"] or "").strip(),
        )
        if value
    ) or "Не указано"

    items = get_user_order_items(user_id)
    products_text = (
        "\n".join(
            (
                f"• {escape(str(item['product_name']))} "
                f"× {int(item['quantity'])}"
            )
            for item in items
        )
        if items
        else "Пока нет заказанных товаров."
    )

    message_text = (
        "👤 <b>Пользователь</b>\n\n"
        f"Telegram ID: <code>{int(user['user_id'])}</code>\n"
        f"Имя: {escape(full_name)}\n"
        f"Username: {username}\n"
        f"Язык: {escape(str(user['language'] or 'ru'))}\n"
        f"Заказов: <b>{int(user['orders_count'])}</b>\n"
        f"Сумма: <b>{int(user['orders_total'])} "
        f"{settings.currency}</b>\n\n"
        "<b>📦 Заказанные товары:</b>\n"
        f"{products_text}"
    )

    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            message_text,
            admin_user_keyboard(user_id),
        )


@dp.callback_query(
    F.data.regexp(r"^admin:user:orders:\d+$")
)
async def admin_user_orders_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    user_id = int(
        str(callback.data).split(":")[3]
    )
    user = get_user(user_id)

    if user is None:
        await callback.answer(
            "Пользователь не найден",
            show_alert=True,
        )
        return

    orders = get_user_orders(
        user_id,
        limit=50,
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "📦 <b>История заказов</b>\n\n"
                f"Telegram ID: <code>{user_id}</code>\n"
                f"Заказов: {len(orders)}"
                if orders
                else (
                    "📦 <b>История заказов</b>\n\n"
                    f"У пользователя <code>{user_id}</code> "
                    "заказов пока нет."
                )
            ),
            admin_user_orders_keyboard(
                user_id,
                orders,
            ),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:user:order:\d+:\d+$"
    )
)
async def admin_user_order_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    parts = str(callback.data).split(":")
    user_id = int(parts[3])
    order_id = int(parts[4])
    order = get_order(order_id)

    if (
        order is None
        or int(order["user_id"]) != user_id
    ):
        await callback.answer(
            "Заказ пользователя не найден",
            show_alert=True,
        )
        return

    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            format_admin_order(
                order,
                get_order_items(order_id),
            ),
            admin_user_order_keyboard(
                user_id,
                order_id,
            ),
        )


# ----------------------------------------------------------------------
# Администратор — категории
# ----------------------------------------------------------------------

@dp.callback_query(F.data == "admin:categories")
async def admin_categories_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await callback.answer()

    if callback.message:
        await show_admin_categories(
            callback.message
        )


@dp.callback_query(
    F.data.regexp(r"^admin:category:\d+$")
)
async def admin_category_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[2]
    )
    await callback.answer()

    if callback.message:
        await show_admin_category(
            callback.message,
            category_id,
        )


@dp.callback_query(
    F.data == "admin:category:add"
)
async def admin_category_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await state.set_state(
        AdminCategoryCreateState.name_ru
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            "Введите название категории на русском:",
            admin_cancel_keyboard(),
        )


@dp.message(AdminCategoryCreateState.name_ru)
async def admin_category_create_ru(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_ru=value)
    await state.set_state(
        AdminCategoryCreateState.name_cs
    )
    await message.answer(
        "Введите название на чешском:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryCreateState.name_cs)
async def admin_category_create_cs(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_cs=value)
    await state.set_state(
        AdminCategoryCreateState.name_uk
    )
    await message.answer(
        "Введите название на украинском:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryCreateState.name_uk)
async def admin_category_create_uk(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_uk=value)
    await state.set_state(
        AdminCategoryCreateState.sort_order
    )
    await message.answer(
        "Введите порядок сортировки, например 10:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryCreateState.sort_order)
async def admin_category_create_sort(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    try:
        sort_order = int(
            (message.text or "").strip()
        )
    except ValueError:
        await message.answer(
            "Введите целое число."
        )
        return

    data = await state.get_data()

    try:
        create_category(
            name_ru=str(data["name_ru"]),
            name_cs=str(data["name_cs"]),
            name_uk=str(data["name_uk"]),
            sort_order=sort_order,
        )
    except (KeyError, ValueError) as error:
        await state.clear()
        await message.answer(
            f"Ошибка: {escape(str(error))}",
            reply_markup=admin_main_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        "✅ Категория создана.",
        reply_markup=admin_main_keyboard(),
    )


@dp.callback_query(
    F.data.regexp(
        r"^admin:category:edit:\d+$"
    )
)
async def admin_category_edit_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[3]
    )
    category = get_category(category_id)

    if category is None:
        await callback.answer(
            "Категория не найдена",
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(
        category_id=category_id
    )
    await state.set_state(
        AdminCategoryEditState.name_ru
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "Введите новое русское название.\n"
                f"Текущее: "
                f"{escape(str(category['name_ru']))}"
            ),
            admin_cancel_keyboard(),
        )


@dp.message(AdminCategoryEditState.name_ru)
async def admin_category_edit_ru(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_ru=value)
    await state.set_state(
        AdminCategoryEditState.name_cs
    )
    await message.answer(
        "Введите новое чешское название:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryEditState.name_cs)
async def admin_category_edit_cs(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_cs=value)
    await state.set_state(
        AdminCategoryEditState.name_uk
    )
    await message.answer(
        "Введите новое украинское название:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryEditState.name_uk)
async def admin_category_edit_uk(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    value = (message.text or "").strip()

    if not value:
        await message.answer(
            "Название не может быть пустым."
        )
        return

    await state.update_data(name_uk=value)
    await state.set_state(
        AdminCategoryEditState.sort_order
    )
    await message.answer(
        "Введите новый порядок сортировки:",
        reply_markup=admin_cancel_keyboard(),
    )


@dp.message(AdminCategoryEditState.sort_order)
async def admin_category_edit_sort(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    try:
        sort_order = int(
            (message.text or "").strip()
        )
    except ValueError:
        await message.answer(
            "Введите целое число."
        )
        return

    data = await state.get_data()

    try:
        updated = update_category(
            category_id=int(data["category_id"]),
            name_ru=str(data["name_ru"]),
            name_cs=str(data["name_cs"]),
            name_uk=str(data["name_uk"]),
            sort_order=sort_order,
        )
    except (KeyError, ValueError) as error:
        await state.clear()
        await message.answer(
            f"Ошибка: {escape(str(error))}",
            reply_markup=admin_main_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        (
            "✅ Категория изменена."
            if updated
            else "Категория не найдена."
        ),
        reply_markup=admin_main_keyboard(),
    )


@dp.callback_query(
    F.data.regexp(
        r"^admin:category:toggle:\d+$"
    )
)
async def admin_category_toggle_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[3]
    )
    category = get_category(category_id)

    if category is None:
        await callback.answer(
            "Категория не найдена",
            show_alert=True,
        )
        return

    set_category_active(
        category_id,
        not bool(category["is_active"]),
    )
    await callback.answer("Статус изменён")

    if callback.message:
        await show_admin_category(
            callback.message,
            category_id,
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:category:delete:\d+$"
    )
)
async def admin_category_delete_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[3]
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "Удалить категорию?\n\n"
                "Категорию с товарами удалить нельзя."
            ),
            admin_category_delete_keyboard(
                category_id
            ),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:category:delete_confirm:\d+$"
    )
)
async def admin_category_delete_confirm_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[3]
    )

    if not delete_category(category_id):
        await callback.answer(
            "Категория содержит товары "
            "или уже удалена.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Категория удалена"
    )

    if callback.message:
        await show_admin_categories(
            callback.message
        )


@dp.callback_query(
    F.data == "admin:category:cancel"
)
async def admin_category_cancel_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await callback.answer("Отменено")

    if callback.message:
        await show_admin_categories(
            callback.message
        )


# ----------------------------------------------------------------------
# Администратор — товары
# ----------------------------------------------------------------------

@dp.callback_query(F.data == "admin:products")
async def admin_products_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await callback.answer()

    if callback.message:
        await show_admin_products(
            callback.message
        )


@dp.callback_query(
    F.data == "admin:product:add"
)
async def admin_product_add_callback(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    categories = get_categories(
        active_only=True
    )

    if not categories:
        await callback.answer(
            "Сначала создайте активную категорию.",
            show_alert=True,
        )
        return

    await state.clear()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            "Выберите категорию товара:",
            admin_product_categories_keyboard(
                categories,
                "create",
            ),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:create:category:\d+$"
    )
)
async def admin_product_create_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[4]
    )
    category = get_category(category_id)

    if (
        category is None
        or not bool(category["is_active"])
    ):
        await callback.answer(
            "Категория не найдена или скрыта",
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(
        category_id=category_id
    )
    await state.set_state(
        AdminProductCreateState.name_ru
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            "Введите название товара на русском:",
            admin_product_cancel_keyboard(),
        )


@dp.message(AdminProductCreateState.name_ru)
async def product_create_name_ru(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.name_cs,
        "name_ru",
        message.text or "",
        "Введите название на чешском:",
    )


@dp.message(AdminProductCreateState.name_cs)
async def product_create_name_cs(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.name_uk,
        "name_cs",
        message.text or "",
        "Введите название на украинском:",
    )


@dp.message(AdminProductCreateState.name_uk)
async def product_create_name_uk(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.description_ru,
        "name_uk",
        message.text or "",
        "Введите описание на русском:",
    )


@dp.message(AdminProductCreateState.description_ru)
async def product_create_description_ru(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.description_cs,
        "description_ru",
        message.text or "",
        "Введите описание на чешском:",
    )


@dp.message(AdminProductCreateState.description_cs)
async def product_create_description_cs(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.description_uk,
        "description_cs",
        message.text or "",
        "Введите описание на украинском:",
    )


@dp.message(AdminProductCreateState.description_uk)
async def product_create_description_uk(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductCreateState.price,
        "description_uk",
        message.text or "",
        (
            "Введите цену целым числом "
            f"в {settings.currency}:"
        ),
    )


@dp.message(AdminProductCreateState.price)
async def product_create_price(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    try:
        price = int(
            (message.text or "").strip()
        )
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введите положительное целое число."
        )
        return

    await state.update_data(price=price)
    await state.set_state(
        AdminProductCreateState.photo
    )
    await message.answer(
        "Отправьте фотографию товара.",
        reply_markup=(
            admin_product_cancel_keyboard()
        ),
    )


@dp.message(
    AdminProductCreateState.photo,
    F.photo,
)
async def product_create_photo(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    data = await state.get_data()

    try:
        product_id = create_product(
            category_id=int(data["category_id"]),
            code=(
                f"PRODUCT-{message.from_user.id}-"
                f"{message.message_id}"
            ),
            name_ru=str(data["name_ru"]),
            name_cs=str(data["name_cs"]),
            name_uk=str(data["name_uk"]),
            description_ru=str(
                data["description_ru"]
            ),
            description_cs=str(
                data["description_cs"]
            ),
            description_uk=str(
                data["description_uk"]
            ),
            price=int(data["price"]),
            stock=0,
            photo=message.photo[-1].file_id,
            sort_order=0,
        )
    except (KeyError, ValueError) as error:
        await state.clear()
        await message.answer(
            f"Ошибка: {escape(str(error))}",
            reply_markup=admin_main_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        f"✅ Товар создан. ID: {product_id}",
        reply_markup=admin_main_keyboard(),
    )


@dp.message(AdminProductCreateState.photo)
async def product_create_photo_invalid(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    await message.answer(
        "Отправьте фото как изображение, не как файл.",
        reply_markup=(
            admin_product_cancel_keyboard()
        ),
    )


@dp.callback_query(
    F.data.regexp(r"^admin:product:\d+$")
)
async def admin_product_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[2]
    )
    await callback.answer()

    if callback.message:
        await show_admin_product(
            callback.message,
            product_id,
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:toggle:\d+$"
    )
)
async def admin_product_toggle(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[3]
    )
    product = get_product(product_id)

    if product is None:
        await callback.answer(
            "Товар не найден",
            show_alert=True,
        )
        return

    set_product_active(
        product_id,
        not bool(product["is_active"]),
    )
    await callback.answer("Статус изменён")

    if callback.message:
        await show_admin_product(
            callback.message,
            product_id,
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:photo:\d+$"
    )
)
async def admin_product_photo_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[3]
    )

    if get_product(product_id) is None:
        await callback.answer(
            "Товар не найден",
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(
        product_id=product_id
    )
    await state.set_state(
        AdminProductPhotoState.photo
    )
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "Отправьте новое фото товара.",
            reply_markup=(
                admin_product_cancel_keyboard()
            ),
        )


@dp.message(
    AdminProductPhotoState.photo,
    F.photo,
)
async def admin_product_photo_save(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    data = await state.get_data()

    try:
        product_id = int(
            data["product_id"]
        )
    except (KeyError, TypeError, ValueError):
        await state.clear()
        await message.answer(
            "Данные редактирования потеряны.",
            reply_markup=admin_main_keyboard(),
        )
        return

    updated = set_product_photo(
        product_id,
        message.photo[-1].file_id,
    )
    await state.clear()

    await message.answer(
        (
            "✅ Фото изменено."
            if updated
            else "Товар не найден."
        ),
        reply_markup=admin_main_keyboard(),
    )


@dp.message(AdminProductPhotoState.photo)
async def admin_product_photo_invalid(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    await message.answer(
        "Отправьте фото как изображение.",
        reply_markup=(
            admin_product_cancel_keyboard()
        ),
    )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:delete:\d+$"
    )
)
async def admin_product_delete_start(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[3]
    )

    if get_product(product_id) is None:
        await callback.answer(
            "Товар не найден",
            show_alert=True,
        )
        return

    await callback.answer()

    if callback.message:
        if callback.message.photo:
            await callback.message.edit_caption(
                caption="Удалить этот товар?",
                reply_markup=(
                    admin_product_delete_keyboard(
                        product_id
                    )
                ),
            )
        else:
            await callback.message.edit_text(
                "Удалить этот товар?",
                reply_markup=(
                    admin_product_delete_keyboard(
                        product_id
                    )
                ),
            )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:delete_confirm:\d+$"
    )
)
async def admin_product_delete_confirm(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[3]
    )
    deleted = delete_product(product_id)

    if not deleted:
        await callback.answer(
            "Товар есть в заказах. "
            "Его можно только скрыть.",
            show_alert=True,
        )
        return

    await callback.answer("Товар удалён")

    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "✅ Товар удалён.",
            reply_markup=admin_main_keyboard(),
        )


@dp.callback_query(
    F.data == "admin:product:cancel"
)
async def admin_product_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    await state.clear()
    await callback.answer("Отменено")

    if callback.message:
        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "⚙️ <b>Админ-панель Beauty Shop</b>",
            reply_markup=admin_main_keyboard(),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:edit:\d+$"
    )
)
async def admin_product_edit_start(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    product_id = int(
        str(callback.data).split(":")[3]
    )

    if get_product(product_id) is None:
        await callback.answer(
            "Товар не найден",
            show_alert=True,
        )
        return

    categories = get_categories(
        active_only=True
    )

    if not categories:
        await callback.answer(
            "Нет активных категорий.",
            show_alert=True,
        )
        return

    await state.clear()
    await state.update_data(
        product_id=product_id
    )
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "Выберите категорию товара.\n\n"
                "После этого потребуется заново "
                "ввести названия, описания и цену."
            ),
            admin_product_categories_keyboard(
                categories,
                "edit",
            ),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:product:edit:category:\d+$"
    )
)
async def admin_product_edit_category(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    if not await require_admin_callback(callback):
        return

    category_id = int(
        str(callback.data).split(":")[4]
    )
    category = get_category(category_id)
    data = await state.get_data()

    if (
        category is None
        or not bool(category["is_active"])
    ):
        await callback.answer(
            "Категория не найдена или скрыта",
            show_alert=True,
        )
        return

    if "product_id" not in data:
        await callback.answer(
            "Данные редактирования потеряны",
            show_alert=True,
        )
        return

    await state.update_data(
        category_id=category_id
    )
    await state.set_state(
        AdminProductEditState.name_ru
    )
    await callback.answer()

    if callback.message:
        await callback.message.answer(
            "Введите новое название на русском:",
            reply_markup=(
                admin_product_cancel_keyboard()
            ),
        )


@dp.message(AdminProductEditState.name_ru)
async def product_edit_name_ru(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.name_cs,
        "name_ru",
        message.text or "",
        "Введите новое название на чешском:",
    )


@dp.message(AdminProductEditState.name_cs)
async def product_edit_name_cs(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.name_uk,
        "name_cs",
        message.text or "",
        "Введите новое название на украинском:",
    )


@dp.message(AdminProductEditState.name_uk)
async def product_edit_name_uk(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.description_ru,
        "name_uk",
        message.text or "",
        "Введите новое описание на русском:",
    )


@dp.message(AdminProductEditState.description_ru)
async def product_edit_description_ru(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.description_cs,
        "description_ru",
        message.text or "",
        "Введите новое описание на чешском:",
    )


@dp.message(AdminProductEditState.description_cs)
async def product_edit_description_cs(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.description_uk,
        "description_cs",
        message.text or "",
        "Введите новое описание на украинском:",
    )


@dp.message(AdminProductEditState.description_uk)
async def product_edit_description_uk(
    message: Message,
    state: FSMContext,
) -> None:
    await ask_product_field(
        message,
        state,
        AdminProductEditState.price,
        "description_uk",
        message.text or "",
        (
            "Введите новую цену в "
            f"{settings.currency}:"
        ),
    )


@dp.message(AdminProductEditState.price)
async def product_edit_price(
    message: Message,
    state: FSMContext,
) -> None:
    if not await require_admin_message(
        message,
        state,
    ):
        return

    try:
        price = int(
            (message.text or "").strip()
        )
        if price <= 0:
            raise ValueError
    except ValueError:
        await message.answer(
            "Введите положительное целое число."
        )
        return

    data = await state.get_data()

    try:
        updated = update_product(
            product_id=int(data["product_id"]),
            category_id=int(data["category_id"]),
            name_ru=str(data["name_ru"]),
            name_cs=str(data["name_cs"]),
            name_uk=str(data["name_uk"]),
            description_ru=str(
                data["description_ru"]
            ),
            description_cs=str(
                data["description_cs"]
            ),
            description_uk=str(
                data["description_uk"]
            ),
            price=price,
        )
    except (KeyError, ValueError) as error:
        await state.clear()
        await message.answer(
            f"Ошибка: {escape(str(error))}",
            reply_markup=admin_main_keyboard(),
        )
        return

    await state.clear()
    await message.answer(
        (
            "✅ Товар изменён."
            if updated
            else "Товар не найден."
        ),
        reply_markup=admin_main_keyboard(),
    )

# ----------------------------------------------------------------------
# Администратор — заказы
# ----------------------------------------------------------------------


@dp.callback_query(F.data == "admin:orders")
async def admin_orders_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    orders = get_orders(limit=50)
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "📦 <b>Заказы</b>\n\n"
                "Выберите заказ:"
                if orders
                else (
                    "📦 <b>Заказы</b>\n\n"
                    "Заказов пока нет."
                )
            ),
            admin_orders_keyboard(orders),
        )


@dp.callback_query(
    F.data.regexp(r"^admin:order:\d+$")
)
async def admin_order_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    order_id = int(
        str(callback.data).split(":")[2]
    )

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "Заказ не найден",
            show_alert=True,
        )
        return

    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            format_admin_order(
                order,
                get_order_items(order_id),
            ),
            admin_order_keyboard(
                order_id,
                str(order["status"]),
                str(order["delivery_method"]),
            ),
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:order:status:\d+:[a-z_]+$"
    )
)
async def admin_order_status_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    parts = str(callback.data).split(":")
    order_id = int(parts[3])
    status = parts[4]

    if not set_order_status(
        order_id,
        status,
    ):
        await callback.answer(
            "Недопустимый переход статуса.",
            show_alert=True,
        )
        return

    # Получаем заказ повторно,
    # чтобы получить обновлённый статус.
    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "Заказ не найден",
            show_alert=True,
        )
        return

    await callback.answer("Статус изменён")

    if callback.message:
        await replace_message(
            callback.message,
            format_admin_order(
                order,
                get_order_items(order_id),
            ),
            admin_order_keyboard(
                order_id,
                str(order["status"]),
                str(order["delivery_method"]),
            ),
        )

    try:
        await callback.bot.send_message(
            int(order["user_id"]),
            (
                f"📦 Статус заказа #{order_id}: "
                f"{status_name(
                    str(order['status']),
                    str(order['language']),
                )}"
            ),
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить клиента "
            "об изменении статуса"
        )

# ----------------------------------------------------------------------
# Администратор — QR-платежи
# ----------------------------------------------------------------------


@dp.callback_query(F.data == "admin:payments")
async def admin_payments_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    orders = get_payments_for_check()
    await callback.answer()

    if callback.message:
        await replace_message(
            callback.message,
            (
                "💳 <b>QR-платежи на проверке</b>\n\n"
                "Выберите платёж:"
                if orders
                else (
                    "💳 <b>QR-платежи</b>\n\n"
                    "Платежей на проверке нет."
                )
            ),
            admin_payments_keyboard(orders),
        )


@dp.callback_query(
    F.data.regexp(r"^admin:payment:\d+$")
)
async def admin_payment_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    order_id = int(
        str(callback.data).split(":")[2]
    )
    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "Заказ не найден.",
            show_alert=True,
        )
        return

    if str(order["payment_method"]) != "qr":
        await callback.answer(
            "Это не QR-платёж.",
            show_alert=True,
        )
        return

    await callback.answer()

    payment_status = str(
        order["payment_status"]
    )

    # Подтверждение и отклонение доступны только
    # после нажатия клиентом «Я оплатил».
    keyboard = (
        admin_payment_keyboard(order_id)
        if payment_status == "checking"
        else admin_back_keyboard()
    )

    if callback.message:
        await replace_message(
            callback.message,
            (
                "💳 <b>QR-платёж</b>\n\n"
                + format_admin_order(
                    order,
                    get_order_items(order_id),
                )
            ),
            keyboard,
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:payment:confirm:\d+$"
    )
)
async def admin_payment_confirm_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    order_id = int(
        str(callback.data).split(":")[3]
    )

    if not confirm_qr_payment(
        order_id,
        callback.from_user.id,
    ):
        await callback.answer(
            "Платёж уже обработан или не находится "
            "на проверке.",
            show_alert=True,
        )
        return

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "Заказ не найден.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Платёж подтверждён."
    )

    if callback.message:
        await replace_message(
            callback.message,
            (
                "✅ <b>Платёж подтверждён</b>\n\n"
                + format_admin_order(
                    order,
                    get_order_items(order_id),
                )
            ),
            admin_back_keyboard(),
        )

    try:
        await callback.bot.send_message(
            int(order["user_id"]),
            (
                f"✅ Оплата заказа #{order_id} "
                "подтверждена."
            ),
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить клиента "
            "о подтверждении оплаты"
        )


@dp.callback_query(
    F.data.regexp(
        r"^admin:payment:reject:\d+$"
    )
)
async def admin_payment_reject_callback(
    callback: CallbackQuery,
) -> None:
    if not await require_admin_callback(callback):
        return

    order_id = int(
        str(callback.data).split(":")[3]
    )

    if not reject_qr_payment(
        order_id,
        callback.from_user.id,
    ):
        await callback.answer(
            "Платёж уже обработан или не находится "
            "на проверке.",
            show_alert=True,
        )
        return

    order = get_order(order_id)

    if order is None:
        await callback.answer(
            "Заказ не найден.",
            show_alert=True,
        )
        return

    await callback.answer(
        "Платёж отклонён."
    )

    if callback.message:
        await replace_message(
            callback.message,
            (
                "❌ <b>Платёж отклонён</b>\n\n"
                + format_admin_order(
                    order,
                    get_order_items(order_id),
                )
            ),
            admin_back_keyboard(),
        )

    try:
        await callback.bot.send_message(
            int(order["user_id"]),
            (
                f"❌ Оплата заказа #{order_id} "
                "не подтверждена."
            ),
        )
    except Exception:
        logging.exception(
            "Не удалось уведомить клиента "
            "об отклонении оплаты"
        )
# ----------------------------------------------------------------------
# Неизвестные сообщения
# ----------------------------------------------------------------------


@dp.message()
async def unknown_handler(
    message: Message,
) -> None:
    language = register_telegram_user(message)

    # Администратору никогда не показываем
    # нижнее клиентское меню.
    if (
        message.from_user is not None
        and is_admin(message.from_user.id)
    ):
        hide_message = await message.answer(
            "⚙️ Открываю админ-панель…",
            reply_markup=remove_keyboard(),
        )

        try:
            await hide_message.delete()
        except Exception:
            pass

        await message.answer(
            "⚙️ <b>Админ-панель Beauty Shop</b>",
            reply_markup=admin_main_keyboard(),
        )
        return

    # Нижнее меню показывается только клиентам.
    await message.answer(
        text(language, "unknown"),
        reply_markup=main_keyboard(language),
    )


# ----------------------------------------------------------------------
# Запуск
# ----------------------------------------------------------------------

async def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(name)s | %(message)s"
        ),
    )

    create_tables()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
        ),
    )

    await bot.delete_webhook(
        drop_pending_updates=False
    )

    logging.info("Beauty Shop запущен")

    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
