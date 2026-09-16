from __future__ import annotations

import re
import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

from config import (
    DEFAULT_LANGUAGE,
    DELIVERY_METHODS,
    ORDER_STATUS_TRANSITIONS,
    PAYMENT_METHODS,
    SUPPORTED_LANGUAGES,
    settings,
)


def normalize_language(
    language: str | None,
) -> str:
    language = str(
        language or ""
    ).strip().lower()

    return (
        language
        if language in SUPPORTED_LANGUAGES
        else DEFAULT_LANGUAGE
    )


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(
        settings.database_path,
        timeout=30,
    )
    connection.row_factory = sqlite3.Row
    connection.execute(
        "PRAGMA foreign_keys = ON"
    )
    connection.execute(
        "PRAGMA busy_timeout = 30000"
    )

    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def create_tables() -> None:
    with connect() as connection:
        connection.execute(
            "PRAGMA journal_mode = WAL"
        )
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                language TEXT NOT NULL DEFAULT 'ru',
                is_blocked INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name_ru TEXT NOT NULL,
                name_cs TEXT NOT NULL,
                name_uk TEXT NOT NULL,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_id INTEGER NOT NULL,
                code TEXT NOT NULL UNIQUE,
                name_ru TEXT NOT NULL,
                name_cs TEXT NOT NULL,
                name_uk TEXT NOT NULL,
                description_ru TEXT NOT NULL DEFAULT '',
                description_cs TEXT NOT NULL DEFAULT '',
                description_uk TEXT NOT NULL DEFAULT '',
                price INTEGER NOT NULL
                    CHECK(price >= 0),
                stock INTEGER NOT NULL DEFAULT 0
                    CHECK(stock >= 0),
                photo TEXT,
                sort_order INTEGER NOT NULL DEFAULT 0,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(category_id)
                    REFERENCES categories(id)
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS cart_items (
                user_id INTEGER NOT NULL,
                product_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 1
                    CHECK(quantity > 0),
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(user_id, product_id),
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE CASCADE,
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
                    ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                customer_name TEXT NOT NULL,
                phone TEXT NOT NULL,
                address TEXT NOT NULL,
                delivery_method TEXT NOT NULL,
                products_total INTEGER NOT NULL
                    CHECK(products_total >= 0),
                delivery_price INTEGER NOT NULL
                    CHECK(delivery_price >= 0),
                total INTEGER NOT NULL
                    CHECK(total >= 0),
                currency TEXT NOT NULL DEFAULT 'CZK',
                language TEXT NOT NULL DEFAULT 'ru',
                status TEXT NOT NULL DEFAULT 'new',
                payment_method TEXT NOT NULL,
                payment_status TEXT NOT NULL
                    DEFAULT 'pending',
                variable_symbol TEXT,
                payment_checked_by INTEGER,
                payment_checked_at TEXT,
                created_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL
                    DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id)
                    REFERENCES users(user_id)
                    ON DELETE RESTRICT
            );

            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER NOT NULL,
                product_id INTEGER,
                product_code TEXT NOT NULL,
                product_name TEXT NOT NULL,
                price INTEGER NOT NULL
                    CHECK(price >= 0),
                quantity INTEGER NOT NULL
                    CHECK(quantity > 0),
                FOREIGN KEY(order_id)
                    REFERENCES orders(id)
                    ON DELETE CASCADE,
                FOREIGN KEY(product_id)
                    REFERENCES products(id)
                    ON DELETE SET NULL
            );

            CREATE INDEX IF NOT EXISTS
                idx_products_category
                ON products(
                    category_id,
                    is_active,
                    sort_order
                );

            CREATE INDEX IF NOT EXISTS
                idx_orders_user
                ON orders(user_id, created_at);

            CREATE INDEX IF NOT EXISTS
                idx_orders_status
                ON orders(status, payment_status);

            CREATE INDEX IF NOT EXISTS
                idx_order_items_order
                ON order_items(order_id);

            CREATE INDEX IF NOT EXISTS
                idx_cart_items_user
                ON cart_items(user_id);
            """
        )


# ----------------------------------------------------------------------
# Пользователи
# ----------------------------------------------------------------------

def upsert_user(
    user_id: int,
    username: str | None = None,
    first_name: str | None = None,
    last_name: str | None = None,
    language: str | None = None,
) -> None:
    language = normalize_language(language)

    with connect() as connection:
        connection.execute(
            """
            INSERT INTO users (
                user_id,
                username,
                first_name,
                last_name,
                language
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                last_name = excluded.last_name,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                int(user_id),
                username,
                first_name,
                last_name,
                language,
            ),
        )


def set_user_language(
    user_id: int,
    language: str,
) -> None:
    language = normalize_language(language)

    with connect() as connection:
        connection.execute(
            """
            UPDATE users
            SET language = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
            """,
            (
                language,
                int(user_id),
            ),
        )


def get_user_language(
    user_id: int,
) -> str:
    user = get_user(user_id)

    if user is None:
        return DEFAULT_LANGUAGE

    return normalize_language(
        user["language"]
    )


def get_user(
    user_id: int,
) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                users.*,
                COUNT(orders.id) AS orders_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN orders.status
                                 != 'cancelled'
                            THEN orders.total
                            ELSE 0
                        END
                    ),
                    0
                ) AS orders_total
            FROM users
            LEFT JOIN orders
              ON orders.user_id = users.user_id
            WHERE users.user_id = ?
            GROUP BY users.user_id
            """,
            (int(user_id),),
        ).fetchone()


def get_users(
    limit: int = 10,
    offset: int = 0,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                users.*,
                COUNT(orders.id) AS orders_count,
                COALESCE(
                    SUM(
                        CASE
                            WHEN orders.status
                                 != 'cancelled'
                            THEN orders.total
                            ELSE 0
                        END
                    ),
                    0
                ) AS orders_total
            FROM users
            LEFT JOIN orders
              ON orders.user_id = users.user_id
            GROUP BY users.user_id
            ORDER BY users.created_at DESC
            LIMIT ? OFFSET ?
            """,
            (
                max(1, int(limit)),
                max(0, int(offset)),
            ),
        ).fetchall()


def count_users() -> int:
    with connect() as connection:
        row = connection.execute(
            "SELECT COUNT(*) FROM users"
        ).fetchone()

        return int(row[0])


# ----------------------------------------------------------------------
# Категории
# ----------------------------------------------------------------------

def create_category(
    name_ru: str,
    name_cs: str,
    name_uk: str,
    sort_order: int = 0,
) -> int:
    names = [
        str(name_ru or "").strip(),
        str(name_cs or "").strip(),
        str(name_uk or "").strip(),
    ]

    if not all(names):
        raise ValueError(
            "Названия на всех языках обязательны"
        )

    with connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO categories (
                name_ru,
                name_cs,
                name_uk,
                sort_order
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                *names,
                int(sort_order),
            ),
        )

        return int(cursor.lastrowid)


def get_categories(
    active_only: bool = True,
) -> list[sqlite3.Row]:
    query = """
        SELECT *
        FROM categories
    """
    parameters: tuple[Any, ...] = ()

    if active_only:
        query += " WHERE is_active = 1"

    query += " ORDER BY sort_order, id"

    with connect() as connection:
        return connection.execute(
            query,
            parameters,
        ).fetchall()


def get_category(
    category_id: int,
) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM categories
            WHERE id = ?
            """,
            (int(category_id),),
        ).fetchone()


def set_category_active(
    category_id: int,
    is_active: bool,
) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE categories
            SET is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(is_active),
                int(category_id),
            ),
        )

        return cursor.rowcount > 0


def update_category(
    category_id: int,
    name_ru: str,
    name_cs: str,
    name_uk: str,
    sort_order: int = 0,
) -> bool:
    names = [
        str(name_ru or "").strip(),
        str(name_cs or "").strip(),
        str(name_uk or "").strip(),
    ]

    if not all(names):
        raise ValueError(
            "Названия на всех языках обязательны"
        )

    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE categories
            SET name_ru = ?,
                name_cs = ?,
                name_uk = ?,
                sort_order = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                *names,
                int(sort_order),
                int(category_id),
            ),
        )

        return cursor.rowcount > 0


def delete_category(
    category_id: int,
) -> bool:
    with connect() as connection:
        product = connection.execute(
            """
            SELECT 1
            FROM products
            WHERE category_id = ?
            LIMIT 1
            """,
            (int(category_id),),
        ).fetchone()

        if product is not None:
            return False

        cursor = connection.execute(
            """
            DELETE FROM categories
            WHERE id = ?
            """,
            (int(category_id),),
        )

        return cursor.rowcount > 0


# ----------------------------------------------------------------------
# Товары
# ----------------------------------------------------------------------

def create_product(
    category_id: int,
    code: str,
    name_ru: str,
    name_cs: str,
    name_uk: str,
    price: int,
    stock: int = 0,
    description_ru: str = "",
    description_cs: str = "",
    description_uk: str = "",
    photo: str | None = None,
    sort_order: int = 0,
) -> int:
    price = int(price)
    stock = int(stock)

    if price < 0:
        raise ValueError(
            "Цена не может быть отрицательной"
        )

    if stock < 0:
        raise ValueError(
            "Остаток не может быть отрицательным"
        )

    code = str(code or "").strip()
    names = [
        str(name_ru or "").strip(),
        str(name_cs or "").strip(),
        str(name_uk or "").strip(),
    ]

    if not code:
        raise ValueError(
            "Код товара не может быть пустым"
        )

    if not all(names):
        raise ValueError(
            "Названия товара на всех языках обязательны"
        )

    with connect() as connection:
        category = connection.execute(
            """
            SELECT 1
            FROM categories
            WHERE id = ?
            """,
            (int(category_id),),
        ).fetchone()

        if category is None:
            raise ValueError(
                "Категория не найдена"
            )

        cursor = connection.execute(
            """
            INSERT INTO products (
                category_id,
                code,
                name_ru,
                name_cs,
                name_uk,
                description_ru,
                description_cs,
                description_uk,
                price,
                stock,
                photo,
                sort_order
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                int(category_id),
                code,
                *names,
                str(description_ru or "").strip(),
                str(description_cs or "").strip(),
                str(description_uk or "").strip(),
                price,
                stock,
                (
                    str(photo).strip()
                    if photo
                    else None
                ),
                int(sort_order),
            ),
        )

        return int(cursor.lastrowid)


def get_products(
    category_id: int | None = None,
    active_only: bool = True,
) -> list[sqlite3.Row]:
    parameters: list[Any] = []

    with connect() as connection:
        # Автоматически добавляем поле архива.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }

        if "is_deleted" not in columns:
            connection.execute(
                """
                ALTER TABLE products
                ADD COLUMN is_deleted
                INTEGER NOT NULL DEFAULT 0
                """
            )

        conditions: list[str] = [
            "is_deleted = 0"
        ]

        if category_id is not None:
            conditions.append("category_id = ?")
            parameters.append(int(category_id))

        if active_only:
            conditions.append("is_active = 1")

        query = (
            "SELECT * FROM products WHERE "
            + " AND ".join(conditions)
            + " ORDER BY sort_order, id"
        )

        return connection.execute(
            query,
            tuple(parameters),
        ).fetchall()


def get_product(
    product_id: int,
) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM products
            WHERE id = ?
            """,
            (int(product_id),),
        ).fetchone()


def update_product_stock(
    product_id: int,
    stock: int,
) -> bool:
    stock = int(stock)

    if stock < 0:
        raise ValueError(
            "Остаток не может быть отрицательным"
        )

    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET stock = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                stock,
                int(product_id),
            ),
        )

        return cursor.rowcount > 0


def update_product(
    product_id: int,
    category_id: int,
    name_ru: str,
    name_cs: str,
    name_uk: str,
    description_ru: str,
    description_cs: str,
    description_uk: str,
    price: int,
) -> bool:
    price = int(price)
    names = [
        str(name_ru or "").strip(),
        str(name_cs or "").strip(),
        str(name_uk or "").strip(),
    ]

    if price < 0:
        raise ValueError(
            "Цена не может быть отрицательной"
        )

    if not all(names):
        raise ValueError(
            "Названия товара на всех языках обязательны"
        )

    with connect() as connection:
        category = connection.execute(
            """
            SELECT 1
            FROM categories
            WHERE id = ?
            """,
            (int(category_id),),
        ).fetchone()

        if category is None:
            raise ValueError(
                "Категория не найдена"
            )

        cursor = connection.execute(
            """
            UPDATE products
            SET category_id = ?,
                name_ru = ?,
                name_cs = ?,
                name_uk = ?,
                description_ru = ?,
                description_cs = ?,
                description_uk = ?,
                price = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(category_id),
                *names,
                str(description_ru or "").strip(),
                str(description_cs or "").strip(),
                str(description_uk or "").strip(),
                price,
                int(product_id),
            ),
        )

        return cursor.rowcount > 0


def set_product_active(
    product_id: int,
    is_active: bool,
) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET is_active = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                int(is_active),
                int(product_id),
            ),
        )

        return cursor.rowcount > 0


def set_product_photo(
    product_id: int,
    photo: str,
) -> bool:
    photo = str(photo or "").strip()

    if not photo:
        return False

    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE products
            SET photo = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                photo,
                int(product_id),
            ),
        )

        return cursor.rowcount > 0


def delete_product(
    product_id: int,
) -> bool:
    with connect() as connection:
        # Автоматически добавляем поле архива.
        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(products)"
            ).fetchall()
        }

        if "is_deleted" not in columns:
            connection.execute(
                """
                ALTER TABLE products
                ADD COLUMN is_deleted
                INTEGER NOT NULL DEFAULT 0
                """
            )

        product_id = int(product_id)

        used = connection.execute(
            """
            SELECT 1
            FROM order_items
            WHERE product_id = ?
            LIMIT 1
            """,
            (product_id,),
        ).fetchone()

        if used is not None:
            # Товар сохраняется в истории заказов,
            # но исчезает из каталога и админ-панели.
            cursor = connection.execute(
                """
                UPDATE products
                SET is_active = 0,
                    is_deleted = 1
                WHERE id = ?
                  AND is_deleted = 0
                """,
                (product_id,),
            )
        else:
            cursor = connection.execute(
                """
                DELETE FROM products
                WHERE id = ?
                """,
                (product_id,),
            )

        return cursor.rowcount > 0


# ----------------------------------------------------------------------
# Корзина
# ----------------------------------------------------------------------

def add_to_cart(
    user_id: int,
    product_id: int,
    quantity: int = 1,
) -> bool:
    quantity = int(quantity)

    if quantity <= 0:
        return False

    with connect() as connection:
        product = connection.execute(
            """
            SELECT id
            FROM products
            WHERE id = ?
              AND is_active = 1
            """,
            (int(product_id),),
        ).fetchone()

        if product is None:
            return False

        try:
            connection.execute(
                """
                INSERT INTO cart_items (
                    user_id,
                    product_id,
                    quantity
                )
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, product_id)
                DO UPDATE SET
                    quantity = cart_items.quantity
                               + excluded.quantity,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    int(user_id),
                    int(product_id),
                    quantity,
                ),
            )
        except sqlite3.IntegrityError:
            return False

        return True


def set_cart_quantity(
    user_id: int,
    product_id: int,
    quantity: int,
) -> bool:
    quantity = int(quantity)

    with connect() as connection:
        if quantity <= 0:
            cursor = connection.execute(
                """
                DELETE FROM cart_items
                WHERE user_id = ?
                  AND product_id = ?
                """,
                (
                    int(user_id),
                    int(product_id),
                ),
            )

            return cursor.rowcount > 0

        product = connection.execute(
            """
            SELECT id
            FROM products
            WHERE id = ?
              AND is_active = 1
            """,
            (int(product_id),),
        ).fetchone()

        if product is None:
            return False

        cursor = connection.execute(
            """
            UPDATE cart_items
            SET quantity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
              AND product_id = ?
            """,
            (
                quantity,
                int(user_id),
                int(product_id),
            ),
        )

        return cursor.rowcount > 0


def get_cart(
    user_id: int,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                cart_items.product_id,
                cart_items.quantity,
                products.code,
                products.name_ru,
                products.name_cs,
                products.name_uk,
                products.price,
                products.stock,
                products.photo,
                products.is_active
            FROM cart_items
            JOIN products
              ON products.id =
                 cart_items.product_id
            WHERE cart_items.user_id = ?
            ORDER BY
                products.sort_order,
                products.id
            """,
            (int(user_id),),
        ).fetchall()


def clear_cart(
    user_id: int,
) -> None:
    with connect() as connection:
        connection.execute(
            """
            DELETE FROM cart_items
            WHERE user_id = ?
            """,
            (int(user_id),),
        )


# ----------------------------------------------------------------------
# Заказы
# ----------------------------------------------------------------------

def create_order(
    user_id: int,
    customer_name: str,
    phone: str,
    address: str,
    delivery_method: str,
    delivery_price: int,
    language: str,
    payment_method: str,
) -> int | None:
    language = normalize_language(
        language
    )
    payment_method = str(
        payment_method or ""
    ).strip().lower()

    if payment_method not in PAYMENT_METHODS:
        raise ValueError(
            "Неизвестный способ оплаты"
        )

    customer_name = " ".join(
        str(customer_name or "")
        .strip()
        .split()
    )

    if (
        not 2 <= len(customer_name) <= 80
        or not re.fullmatch(
            r"[^\W\d_]+(?:[ '\-][^\W\d_]+)*",
            customer_name,
            flags=re.UNICODE,
        )
    ):
        raise ValueError(
            "Некорректное имя"
        )

    phone = str(phone or "").strip()
    phone_digits = re.sub(
        r"\D",
        "",
        phone,
    )

    if not 7 <= len(phone_digits) <= 15:
        raise ValueError(
            "Некорректный телефон"
        )

    delivery_method = str(
        delivery_method or ""
    ).strip().lower()

    if delivery_method not in DELIVERY_METHODS:
        raise ValueError(
            "Неизвестный способ доставки"
        )

    expected_delivery_price = int(
        DELIVERY_METHODS[delivery_method]
    )
    delivery_price = int(
        delivery_price
    )

    if (
        delivery_price
        != expected_delivery_price
    ):
        raise ValueError(
            "Неверная стоимость доставки"
        )

    address = " ".join(
        str(address or "").strip().split()
    )

    if delivery_method == "pickup":
        address = "Самовывоз"
    elif (
        not 5 <= len(address) <= 200
        or not re.search(
            r"[\w\u00C0-\u024F\u0400-\u04FF]",
            address,
            flags=re.UNICODE,
        )
    ):
        raise ValueError(
            "Некорректный адрес"
        )

    with connect() as connection:
        # Блокирует конкурентную запись до завершения
        # создания заказа и списания остатков.
        connection.execute(
            "BEGIN IMMEDIATE"
        )

        user = connection.execute(
            """
            SELECT 1
            FROM users
            WHERE user_id = ?
            """,
            (int(user_id),),
        ).fetchone()

        if user is None:
            raise ValueError(
                "Пользователь не найден"
            )

        cart = connection.execute(
            """
            SELECT
                cart_items.product_id,
                cart_items.quantity,
                products.code,
                products.name_ru,
                products.name_cs,
                products.name_uk,
                products.price,
                
                products.is_active
            FROM cart_items
            JOIN products
              ON products.id =
                 cart_items.product_id
            WHERE cart_items.user_id = ?
            ORDER BY products.id
            """,
            (int(user_id),),
        ).fetchall()

        if not cart:
            return None

        products_total = 0

        for item in cart:
            quantity = int(item["quantity"])

            if not bool(item["is_active"]):
                raise ValueError(
                    f"Товар {item['code']} больше недоступен"
                )

            products_total += (
                int(item["price"]) * quantity
            )

        total = (
            products_total
            + delivery_price
        )

        cursor = connection.execute(
            """
            INSERT INTO orders (
                user_id,
                customer_name,
                phone,
                address,
                delivery_method,
                products_total,
                delivery_price,
                total,
                currency,
                language,
                payment_method,
                payment_status
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, 'pending'
            )
            """,
            (
                int(user_id),
                customer_name,
                phone,
                address,
                delivery_method,
                products_total,
                delivery_price,
                total,
                settings.currency,
                language,
                payment_method,
            ),
        )

        order_id = int(
            cursor.lastrowid
        )

        for item in cart:
            quantity = int(
                item["quantity"]
            )
            product_id = int(
                item["product_id"]
            )
            product_name = (
                item[f"name_{language}"]
                or item["name_ru"]
            )

            stock_cursor = (
                connection.execute(
                    """
                    UPDATE products
                    SET stock = stock - ?,
                        updated_at =
                            CURRENT_TIMESTAMP
                    WHERE id = ?
                      AND is_active = 1
                      AND stock >= ?
                    """,
                    (
                        quantity,
                        product_id,
                        quantity,
                    ),
                )
            )

            connection.execute(
                """
                INSERT INTO order_items (
                    order_id,
                    product_id,
                    product_code,
                    product_name,
                    price,
                    quantity
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    order_id,
                    product_id,
                    str(item["code"]),
                    str(product_name),
                    int(item["price"]),
                    quantity,
                ),
            )

        if payment_method == "qr":
            connection.execute(
                """
                UPDATE orders
                SET variable_symbol = ?,
                    updated_at =
                        CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (
                    str(order_id),
                    order_id,
                ),
            )

        connection.execute(
            """
            DELETE FROM cart_items
            WHERE user_id = ?
            """,
            (int(user_id),),
        )

        return order_id


def get_order(
    order_id: int,
) -> sqlite3.Row | None:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM orders
            WHERE id = ?
            """,
            (int(order_id),),
        ).fetchone()


def get_order_items(
    order_id: int,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM order_items
            WHERE order_id = ?
            ORDER BY id
            """,
            (int(order_id),),
        ).fetchall()


def get_orders(
    limit: int = 50,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM orders
            ORDER BY id DESC
            LIMIT ?
            """,
            (max(1, int(limit)),),
        ).fetchall()


def get_user_orders(
    user_id: int,
    limit: int = 10,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM orders
            WHERE user_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (
                int(user_id),
                max(1, int(limit)),
            ),
        ).fetchall()


def set_order_status(
    order_id: int,
    status: str,
) -> bool:
    order_id = int(order_id)
    status = str(status).strip().lower()

    with connect() as connection:
        order = connection.execute(
            """
            SELECT status, delivery_method
            FROM orders
            WHERE id = ?
            """,
            (order_id,),
        ).fetchone()

        if order is None:
            return False

        current_status = str(order["status"])
        delivery_method = str(
            order["delivery_method"]
        )

        # Если статус уже установлен.
        if status == current_status:
            return True

        if delivery_method == "pickup":
            # Самовывоз:
            # Новый ⇄ Принят ⇄ Завершён
            transitions = {
                "new": {
                    "accepted",
                    "cancelled",
                },
                "accepted": {
                    "new",
                    "completed",
                    "cancelled",
                },
                "completed": {
                    "accepted",
                },
                "cancelled": set(),
            }
        else:
            # DHL и Zásilkovna:
            # Новый ⇄ Принят ⇄ Упакован
            # ⇄ Отправлен ⇄ Завершён
            transitions = {
                "new": {
                    "accepted",
                    "cancelled",
                },
                "accepted": {
                    "new",
                    "packed",
                    "cancelled",
                },
                "packed": {
                    "accepted",
                    "shipped",
                    "cancelled",
                },
                "shipped": {
                    "packed",
                    "completed",
                    "cancelled",
                },
                "completed": {
                    "shipped",
                },
                "cancelled": set(),
            }

        allowed_statuses = transitions.get(
            current_status,
            set(),
        )

        if status not in allowed_statuses:
            return False

        cursor = connection.execute(
            """
            UPDATE orders
            SET status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND status = ?
            """,
            (
                status,
                order_id,
                current_status,
            ),
        )

        return cursor.rowcount == 1

# ----------------------------------------------------------------------
# QR-платежи
# ----------------------------------------------------------------------


def request_payment_check(
    order_id: int,
    user_id: int,
) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE orders
            SET payment_status = 'checking',
                payment_checked_by = NULL,
                payment_checked_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
              AND user_id = ?
              AND payment_method = 'qr'
              AND status != 'cancelled'
              AND payment_status IN (
                  'pending',
                  'rejected'
              )
            """,
            (
                int(order_id),
                int(user_id),
            ),
        )

        return cursor.rowcount > 0


def confirm_qr_payment(
    order_id: int,
    admin_id: int,
) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE orders
            SET payment_status = 'paid',
                payment_checked_by = ?,
                payment_checked_at =
                    CURRENT_TIMESTAMP,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
              AND payment_method = 'qr'
              AND status != 'cancelled'
              AND payment_status = 'checking'
            """,
            (
                int(admin_id),
                int(order_id),
            ),
        )

        return cursor.rowcount > 0


def reject_qr_payment(
    order_id: int,
    admin_id: int,
) -> bool:
    with connect() as connection:
        cursor = connection.execute(
            """
            UPDATE orders
            SET payment_status = 'rejected',
                payment_checked_by = ?,
                payment_checked_at =
                    CURRENT_TIMESTAMP,
                updated_at =
                    CURRENT_TIMESTAMP
            WHERE id = ?
              AND payment_method = 'qr'
              AND status != 'cancelled'
              AND payment_status = 'checking'
            """,
            (
                int(admin_id),
                int(order_id),
            ),
        )

        return cursor.rowcount > 0


def get_payments_for_check(
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT *
            FROM orders
            WHERE payment_method = 'qr'
              AND payment_status = 'checking'
              AND status != 'cancelled'
            ORDER BY id DESC
            """
        ).fetchall()


# ----------------------------------------------------------------------
# Статистика
# ----------------------------------------------------------------------

def get_statistics() -> sqlite3.Row:
    with connect() as connection:
        row = connection.execute(
            """
            SELECT
                (
                    SELECT COUNT(*)
                    FROM users
                ) AS users_total,
                (
                    SELECT COUNT(*)
                    FROM users
                    WHERE created_at >= datetime(
                        'now',
                        '-1 day'
                    )
                ) AS users_today,
                (
                    SELECT COUNT(*)
                    FROM users
                    WHERE created_at >= datetime(
                        'now',
                        '-7 days'
                    )
                ) AS users_week,
                (
                    SELECT COUNT(*)
                    FROM orders
                ) AS orders_total,
                (
                    SELECT COUNT(*)
                    FROM orders
                    WHERE status = 'new'
                ) AS orders_new,
                (
                    SELECT COALESCE(
                        SUM(total),
                        0
                    )
                    FROM orders
                    WHERE status != 'cancelled'
                ) AS revenue
            """
        ).fetchone()

        if row is None:
            raise RuntimeError(
                "Не удалось получить статистику"
            )

        return row


def get_user_order_items(
    user_id: int,
) -> list[sqlite3.Row]:
    with connect() as connection:
        return connection.execute(
            """
            SELECT
                order_items.product_name,
                SUM(
                    order_items.quantity
                ) AS quantity
            FROM orders
            JOIN order_items
              ON order_items.order_id =
                 orders.id
            WHERE orders.user_id = ?
              AND orders.status != 'cancelled'
            GROUP BY order_items.product_name
            ORDER BY order_items.product_name
            """,
            (int(user_id),),
        ).fetchall()


# ----------------------------------------------------------------------
# Первоначальные данные
# ----------------------------------------------------------------------

def seed_demo_data() -> None:
    with connect() as connection:
        category_count = (
            connection.execute(
                """
                SELECT COUNT(*)
                FROM categories
                """
            ).fetchone()[0]
        )

        if category_count:
            return

        categories = [
            (
                "Уход за лицом",
                "Péče o pleť",
                "Догляд за обличчям",
                10,
            ),
            (
                "Уход за волосами",
                "Péče o vlasy",
                "Догляд за волоссям",
                20,
            ),
            (
                "Макияж",
                "Make-up",
                "Макіяж",
                30,
            ),
        ]

        connection.executemany(
            """
            INSERT INTO categories (
                name_ru,
                name_cs,
                name_uk,
                sort_order
            )
            VALUES (?, ?, ?, ?)
            """,
            categories,
        )
