from __future__ import annotations

from aiogram.utils.keyboard import InlineKeyboardBuilder

from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)

from config import ORDER_STATUS_TRANSITIONS, settings
from texts import localized_value, text


def button_text(
    value: Any,
    limit: int = 60,
) -> str:
    value = " ".join(str(value or "").split())

    if len(value) <= limit:
        return value

    return value[: limit - 1] + "…"


def language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🇷🇺 Русский",
                    callback_data="lang:ru",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇨🇿 Čeština",
                    callback_data="lang:cs",
                )
            ],
            [
                InlineKeyboardButton(
                    text="🇺🇦 Українська",
                    callback_data="lang:uk",
                )
            ],
        ]
    )


def main_keyboard(
    language: str,
) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=text(language, "catalog")
                ),
                KeyboardButton(
                    text=text(language, "cart")
                ),
            ],
            [
                KeyboardButton(
                    text=text(language, "orders")
                ),
                KeyboardButton(
                    text=text(language, "language")
                ),
            ],
            [
                KeyboardButton(
                    text=text(language, "contacts")
                )
            ],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard(
    language: str,
) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=text(language, "cancel")
                )
            ]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def contact_keyboard(
    language: str,
) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(
                    text=text(
                        language,
                        "share_phone",
                    ),
                    request_contact=True,
                )
            ],
            [
                KeyboardButton(
                    text=text(language, "cancel")
                )
            ],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def categories_keyboard(
    categories: list[Any],
    language: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        name = localized_value(
            category,
            "name",
            language,
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(name),
                    callback_data=(
                        f"category:{category['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=text(language, "back"),
                callback_data="main:back",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def products_keyboard(
    products: list[Any],
    language: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for product in products:
        name = localized_value(
            product,
            "name",
            language,
        )
        label = (
            f"{name} — {product['price']} "
            f"{settings.currency}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"product:{product['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=text(language, "back"),
                callback_data="catalog:categories",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def product_keyboard(
    product_id: int,
    category_id: int,
    language: str,
    in_stock: bool,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    if in_stock:
        rows.append(
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "add_to_cart",
                    ),
                    callback_data=(
                        f"cart:add:{product_id}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text=text(language, "back"),
                callback_data=(
                    f"category:{category_id}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def cart_keyboard(
    cart: list[Any],
    language: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for item in cart:
        product_id = int(item["product_id"])
        quantity = int(item["quantity"])
        name = localized_value(
            item,
            "name",
            language,
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text="➖",
                    callback_data=(
                        f"cart:minus:{product_id}"
                    ),
                ),
                InlineKeyboardButton(
                    text=button_text(
                        f"{name}: {quantity}",
                        50,
                    ),
                    callback_data="noop",
                ),
                InlineKeyboardButton(
                    text="➕",
                    callback_data=(
                        f"cart:plus:{product_id}"
                    ),
                ),
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "checkout",
                    ),
                    callback_data="checkout:start",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "clear_cart",
                    ),
                    callback_data="cart:clear",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def delivery_keyboard(
    language: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "zasilkovna",
                        price=(
                            settings.zasilkovna_price
                        ),
                        currency=settings.currency,
                    ),
                    callback_data=(
                        "checkout:delivery:zasilkovna"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "dhl",
                        price=settings.dhl_price,
                        currency=settings.currency,
                    ),
                    callback_data=(
                        "checkout:delivery:dhl"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "pickup",
                    ),
                    callback_data=(
                        "checkout:delivery:pickup"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(language, "cancel"),
                    callback_data="checkout:cancel",
                )
            ],
        ]
    )


def payment_keyboard(
    language: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text(language, "cash"),
                    callback_data="checkout:payment:cash",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(language, "qr"),
                    callback_data="checkout:payment:qr",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(language, "back_delivery"),
                    callback_data="checkout:back:delivery",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(language, "cancel"),
                    callback_data="checkout:cancel",
                )
            ],
        ]
    )


def order_confirmation_keyboard(
    language: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text(language, "confirm"),
                    callback_data="checkout:confirm",
                )
            ],
            [
                InlineKeyboardButton(
                    text=text(language, "cancel"),
                    callback_data="checkout:cancel",
                )
            ],
        ]
    )


def remove_keyboard() -> ReplyKeyboardRemove:
    return ReplyKeyboardRemove()


def payment_check_keyboard(
    order_id: int,
    language: str,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=text(
                        language,
                        "payment_sent",
                    ),
                    callback_data=(
                        f"payment:check:{order_id}"
                    ),
                )
            ]
        ]
    )


# ----------------------------------------------------------------------
# Административные клавиатуры
# ----------------------------------------------------------------------

def admin_main_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 Заказы",
                    callback_data="admin:orders",
                ),
                InlineKeyboardButton(
                    text="💳 QR-платежи",
                    callback_data="admin:payments",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="🗂 Категории",
                    callback_data="admin:categories",
                ),
                InlineKeyboardButton(
                    text="🧴 Товары",
                    callback_data="admin:products",
                ),
            ],
            [
                InlineKeyboardButton(
                    text="👥 Пользователи",
                    callback_data="admin:users:0",
                ),
                InlineKeyboardButton(
                    text="📊 Статистика",
                    callback_data="admin:stats",
                ),
            ],
        ]
    )


def admin_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⬅️ В админку",
                    callback_data="admin:main",
                )
            ]
        ]
    )


def admin_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        "admin:category:cancel"
                    ),
                )
            ]
        ]
    )


def admin_categories_keyboard(
    categories: list[Any],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        status = (
            "✅"
            if bool(category["is_active"])
            else "🚫"
        )

        label = (
            f"{status} #{category['id']} "
            f"{category['name_ru']}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"admin:category:"
                        f"{category['id']}"
                    ),
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Добавить категорию",
                    callback_data=(
                        "admin:category:add"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ В админку",
                    callback_data="admin:main",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_category_keyboard(
    category_id: int,
    is_active: bool,
) -> InlineKeyboardMarkup:
    toggle_text = (
        "🚫 Скрыть"
        if is_active
        else "✅ Показать"
    )

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Изменить",
                    callback_data=(
                        f"admin:category:edit:"
                        f"{category_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=(
                        f"admin:category:toggle:"
                        f"{category_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=(
                        f"admin:category:delete:"
                        f"{category_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К категориям",
                    callback_data="admin:categories",
                )
            ],
        ]
    )


def admin_category_delete_keyboard(
    category_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=(
                        "admin:category:"
                        "delete_confirm:"
                        f"{category_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        f"admin:category:"
                        f"{category_id}"
                    ),
                )
            ],
        ]
    )


def admin_products_keyboard(
    products: list[Any],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for product in products:
        status = (
            "✅"
            if bool(product["is_active"])
            else "🚫"
        )
        label = (
            f"{status} #{product['id']} "
            f"{product['name_ru']}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"admin:product:"
                        f"{product['id']}"
                    ),
                )
            ]
        )

    rows.extend(
        [
            [
                InlineKeyboardButton(
                    text="➕ Добавить товар",
                    callback_data=(
                        "admin:product:add"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ В админку",
                    callback_data="admin:main",
                )
            ],
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_product_categories_keyboard(
    categories: list[Any],
    action: str,
) -> InlineKeyboardMarkup:
    if action not in {"create", "edit"}:
        raise ValueError(
            "Неизвестное действие с товаром"
        )

    rows: list[list[InlineKeyboardButton]] = []

    for category in categories:
        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(
                        category["name_ru"]
                    ),
                    callback_data=(
                        f"admin:product:{action}:"
                        f"category:{category['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="❌ Отмена",
                callback_data=(
                    "admin:product:cancel"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_product_keyboard(
    product_id: int,
    is_active: bool,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✏️ Редактировать",
                    callback_data=(
                        f"admin:product:edit:"
                        f"{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🖼 Заменить фото",
                    callback_data=(
                        f"admin:product:photo:"
                        f"{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text=(
                        "🚫 Скрыть"
                        if is_active
                        else "✅ Показать"
                    ),
                    callback_data=(
                        f"admin:product:toggle:"
                        f"{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑 Удалить",
                    callback_data=(
                        f"admin:product:delete:"
                        f"{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К товарам",
                    callback_data="admin:products",
                )
            ],
        ]
    )


def admin_product_delete_keyboard(
    product_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить",
                    callback_data=(
                        "admin:product:"
                        "delete_confirm:"
                        f"{product_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Отмена",
                    callback_data=(
                        f"admin:product:{product_id}"
                    ),
                )
            ],
        ]
    )


def admin_product_cancel_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data=(
                        "admin:product:cancel"
                    ),
                )
            ]
        ]
    )


def admin_new_order_keyboard(
    order_id: int,
    payment_method: str,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = [
        [
            InlineKeyboardButton(
                text="📦 Открыть заказ",
                callback_data=(
                    f"admin:order:{order_id}"
                ),
            )
        ]
    ]

    if payment_method == "qr":
        rows.append(
            [
                InlineKeyboardButton(
                    text="💳 QR-платежи",
                    callback_data="admin:payments",
                )
            ]
        )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# ----------------------------------------------------------------------
# Пользователи
# ----------------------------------------------------------------------

def admin_users_keyboard(
    page: int,
    total: int,
    page_size: int = 10,
    users: list[Any] | None = None,
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for user in users or []:
        full_name = " ".join(
            part
            for part in (
                str(user["first_name"] or "").strip(),
                str(user["last_name"] or "").strip(),
            )
            if part
        ) or "Без имени"

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(
                        f"👤 {full_name} · "
                        f"{user['orders_count']} заказов"
                    ),
                    callback_data=(
                        f"admin:user:{user['user_id']}"
                    ),
                )
            ]
        )

    navigation: list[InlineKeyboardButton] = []

    if page > 0:
        navigation.append(
            InlineKeyboardButton(
                text="⬅️ Назад",
                callback_data=(
                    f"admin:users:{page - 1}"
                ),
            )
        )

    if (page + 1) * page_size < total:
        navigation.append(
            InlineKeyboardButton(
                text="Вперёд ➡️",
                callback_data=(
                    f"admin:users:{page + 1}"
                ),
            )
        )

    if navigation:
        rows.append(navigation)

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ В админку",
                callback_data="admin:main",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_user_keyboard(
    user_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📦 История заказов",
                    callback_data=(
                        f"admin:user:orders:{user_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К пользователям",
                    callback_data="admin:users:0",
                )
            ],
        ]
    )


def admin_user_orders_keyboard(
    user_id: int,
    orders: list[Any],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for order in orders:
        label = (
            f"Заказ #{order['id']} · "
            f"{order['total']} "
            f"{order['currency']} · "
            f"{order['status']}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"admin:user:order:"
                        f"{user_id}:{order['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ К пользователю",
                callback_data=(
                    f"admin:user:{user_id}"
                ),
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_user_order_keyboard(
    user_id: int,
    order_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="⚙️ Управлять заказом",
                    callback_data=(
                        f"admin:order:{order_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К истории заказов",
                    callback_data=(
                        f"admin:user:orders:{user_id}"
                    ),
                )
            ],
        ]
    )


# ----------------------------------------------------------------------
# Заказы
# ----------------------------------------------------------------------

ORDER_STATUS_TITLES = {
    "new": "🆕 Новый",
    "accepted": "✅ Принят",
    "packed": "📦 Упакован",
    "shipped": "🚚 Отправлен",
    "completed": "🏁 Завершён",
    "cancelled": "❌ Отменён",
}

ORDER_STATUS_BUTTONS = {
    "accepted": "✅ Принять",
    "packed": "📦 Упакован",
    "shipped": "🚚 Отправлен",
    "completed": "🏁 Завершён",
    "cancelled": "❌ Отменить",
}


def admin_orders_keyboard(
    orders: list[Any],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for order in orders:
        status = ORDER_STATUS_TITLES.get(
            str(order["status"]),
            str(order["status"]),
        )
        label = (
            f"#{order['id']} · {status} · "
            f"{order['total']} "
            f"{order['currency']}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"admin:order:{order['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ В админку",
                callback_data="admin:main",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_order_keyboard(
    order_id: int,
    status: str,
    delivery_method: str,
):
    builder = InlineKeyboardBuilder()

    if delivery_method == "pickup":
        # Самовывоз
        next_status = {
            "new": ("✅ Принять", "accepted"),
            "accepted": ("🏁 Завершить", "completed"),
        }

        previous_status = {
            "accepted": "new",
            "completed": "accepted",
        }
    else:
        # DHL и Zásilkovna
        next_status = {
            "new": ("✅ Принять", "accepted"),
            "accepted": ("📦 Упакован", "packed"),
            "packed": ("🚚 Отправлен", "shipped"),
            "shipped": ("🏁 Завершить", "completed"),
        }

        previous_status = {
            "accepted": "new",
            "packed": "accepted",
            "shipped": "packed",
            "completed": "shipped",
        }

    # Переход на следующий статус
    if status in next_status:
        button_text, new_status = next_status[status]

        builder.button(
            text=button_text,
            callback_data=(
                f"admin:order:status:"
                f"{order_id}:{new_status}"
            ),
        )

    # Возврат на предыдущий статус
    if status in previous_status:
        old_status = previous_status[status]

        builder.button(
            text="↩️ Предыдущий статус",
            callback_data=(
                f"admin:order:status:"
                f"{order_id}:{old_status}"
            ),
        )

    if status not in {"completed", "cancelled"}:
        builder.button(
            text="❌ Отменить заказ",
            callback_data=(
                f"admin:order:status:"
                f"{order_id}:cancelled"
            ),
        )

    builder.button(
        text="⬅️ К списку заказов",
        callback_data="admin:orders",
    )

    builder.adjust(1)

    return builder.as_markup()

# ----------------------------------------------------------------------
# Платежи
# ----------------------------------------------------------------------


def admin_payments_keyboard(
    orders: list[Any],
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []

    for order in orders:
        label = (
            f"💳 Заказ #{order['id']} · "
            f"{order['total']} "
            f"{order['currency']}"
        )

        rows.append(
            [
                InlineKeyboardButton(
                    text=button_text(label),
                    callback_data=(
                        f"admin:payment:{order['id']}"
                    ),
                )
            ]
        )

    rows.append(
        [
            InlineKeyboardButton(
                text="⬅️ В админку",
                callback_data="admin:main",
            )
        ]
    )

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


def admin_payment_keyboard(
    order_id: int,
) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=(
                        f"admin:payment:confirm:"
                        f"{order_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Отклонить",
                    callback_data=(
                        f"admin:payment:reject:"
                        f"{order_id}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ К QR-платежам",
                    callback_data="admin:payments",
                )
            ],
        ]
    )
