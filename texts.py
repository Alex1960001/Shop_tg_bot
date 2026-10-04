from __future__ import annotations

import logging
from typing import Any

from config import DEFAULT_LANGUAGE, SUPPORTED_LANGUAGES


TEXTS: dict[str, dict[str, str]] = {
    "ru": {
        "language_title": "🌐 Выберите язык:",
        "language_saved": "✅ Язык изменён.",
        "welcome": (
            "🧴 <b>Добро пожаловать в Beauty Shop!</b>\n\n"
            "Выберите нужный раздел:"
        ),
        "main_menu": "🏠 Главное меню",
        "catalog": "🛍 Каталог",
        "cart": "🛒 Корзина",
        "orders": "📦 Мои заказы",
        "language": "🌐 Язык",
        "contacts": "☎️ Контакты",
        "back": "⬅️ Назад",
        "cancel": "❌ Отмена",
        "categories_title": "🗂 Выберите категорию:",
        "category_empty": "В этой категории пока нет товаров.",
        "catalog_empty": "Каталог пока пуст.",
        "product_price": "Цена: <b>{price} {currency}</b>",
        "choose_volume": "Выберите объём:",
        "product_variants": "Доступные объёмы:",
        "out_of_stock": "Нет в наличии",
        "add_to_cart": "➕ В корзину",
        "added_to_cart": "✅ Товар добавлен в корзину.",
        "add_failed": (
            "Не удалось добавить товар. "
            "Возможно, его нет в наличии."
        ),
        "cart_empty": "🛒 Ваша корзина пуста.",
        "cart_title": "🛒 <b>Ваша корзина</b>",
        "cart_item": (
            "• {name}\n"
            "  {quantity} × {price} = {subtotal} {currency}"
        ),
        "cart_total": (
            "Итого без доставки: <b>{total} {currency}</b>"
        ),
        "checkout": "✅ Оформить заказ",
        "clear_cart": "🗑 Очистить корзину",
        "cart_cleared": "Корзина очищена.",
        "quantity_changed": "Количество изменено.",
        "checkout_name": "Введите имя получателя:",
        "checkout_phone": (
            "Нажмите кнопку ниже, чтобы поделиться "
            "своим номером телефона:"
        ),
        "share_phone": "📱 Отправить мой номер",
        "checkout_address": "Введите адрес доставки:",
        "choose_delivery": "Выберите способ доставки:",
        "choose_payment": "Выберите способ оплаты:",
        "zasilkovna": (
            "📦 Zásilkovna — {price} {currency}"
        ),
        "dhl": "🚚 DHL — {price} {currency}",
        "pickup": "🏠 Самовывоз — бесплатно",
        "cash": "💵 Наличными",
        "qr": "📱 QR-перевод",
        "confirm_order": (
            "Проверьте заказ:\n\n"
            "👤 {name}\n"
            "☎️ {phone}\n"
            "📍 {address}\n"
            "🚚 {delivery}\n"
            "💳 {payment}\n\n"
            "Товары: {products_total} {currency}\n"
            "Доставка: {delivery_price} {currency}\n"
            "<b>Итого: {total} {currency}</b>"
        ),
        "confirm": "✅ Подтвердить",
        "order_created": (
            "✅ Заказ <b>№{order_id}</b> создан.\n"
            "Сумма: <b>{total} {currency}</b>"
        ),
        "order_failed": "Не удалось создать заказ.",
        "my_orders_empty": "У вас пока нет заказов.",
        "contacts_text": (
            "☎️ <b>Beauty Shop</b>\n\n"
            "По вопросам заказа свяжитесь "
            "с администратором."
        ),
        "unknown": "Используйте кнопки меню.",
        "admin_only": (
            "Эта команда доступна администратору."
        ),
        "invalid_name": (
            "Введите корректное имя, минимум 2 символа."
        ),
        "invalid_phone": (
            "Нажмите кнопку «Отправить мой номер»."
        ),
        "invalid_address": (
            "Введите полный адрес доставки."
        ),
        "checkout_cancelled": (
            "Оформление заказа отменено."
        ),
        "checkout_data_lost": (
            "Данные оформления потеряны. Начните заново."
        ),
        "cart_changed": (
            "Состав корзины изменился или товара "
            "недостаточно. Проверьте корзину."
        ),
        "delivery_zasilkovna": "Zásilkovna",
        "delivery_dhl": "DHL",
        "delivery_pickup": "Самовывоз",
        "payment_cash": "Наличными",
        "payment_qr": "QR-перевод",
        "order_status": "Статус: {status}",
        "payment_status": "Оплата: {status}",
        "order_summary": (
            "📦 <b>Заказ №{order_id}</b>\n"
            "Сумма: <b>{total} {currency}</b>\n"
            "Статус: {status}\n"
            "Оплата: {payment_status}"
        ),
        "payment_qr_instructions": (
            "📱 <b>Оплата заказа №{order_id}</b>\n\n"
            "Получатель: <b>{recipient}</b>\n"
            "IBAN: <code>{iban}</code>\n"
            "Сумма: <b>{total} {currency}</b>\n"
            "Переменный символ: "
            "<code>{variable_symbol}</code>\n\n"
            "После оплаты нажмите кнопку ниже."
        ),
        "payment_qr_not_configured": (
            "Заказ создан, но IBAN пока не настроен. "
            "Администратор свяжется с вами."
        ),
        "payment_sent": "✅ Я оплатил",
        "payment_check_requested": (
            "✅ Запрос на проверку оплаты отправлен "
            "администратору."
        ),
        "payment_check_failed": (
            "Не удалось отправить запрос. "
            "Возможно, он уже отправлен."
        ),
        "pickup_info": (
            "🏠 <b>Самовывоз</b>\n\n"
            "📍 Адрес: {address}\n"
            "🕐 Время выдачи: {hours}"
        ),
        "back_delivery": "⬅️ Изменить доставку",
        "contacts_text": (
            "📞 <b>Контакты</b>\n\n"
            "Телефон: <a href=\"tel:+420608888151\">"
            "+420 608 888 151</a>\n"
            "Instagram: "
            "<a href=\"https://instagram.com/natalia_siedunova_hairdresser\">"
            "@natalia_siedunova_hairdresser</a>"
        ),

    },
    "cs": {
        "language_title": "🌐 Vyberte jazyk:",
        "language_saved": "✅ Jazyk byl změněn.",
        "welcome": (
            "🧴 <b>Vítejte v Beauty Shop!</b>\n\n"
            "Vyberte požadovanou sekci:"
        ),
        "main_menu": "🏠 Hlavní nabídka",
        "catalog": "🛍 Katalog",
        "cart": "🛒 Košík",
        "orders": "📦 Moje objednávky",
        "language": "🌐 Jazyk",
        "contacts": "☎️ Kontakty",
        "back": "⬅️ Zpět",
        "cancel": "❌ Zrušit",
        "categories_title": "🗂 Vyberte kategorii:",
        "category_empty": (
            "V této kategorii zatím nejsou produkty."
        ),
        "catalog_empty": "Katalog je zatím prázdný.",
        "product_price": "Cena: <b>{price} {currency}</b>",
        "choose_volume": "Vyberte objem:",
        "product_variants": "Dostupné objemy:",
        "out_of_stock": "Není skladem",
        "add_to_cart": "➕ Do košíku",
        "added_to_cart": (
            "✅ Produkt byl přidán do košíku."
        ),
        "add_failed": (
            "Produkt nelze přidat. "
            "Pravděpodobně není skladem."
        ),
        "cart_empty": "🛒 Váš košík je prázdný.",
        "cart_title": "🛒 <b>Váš košík</b>",
        "cart_item": (
            "• {name}\n"
            "  {quantity} × {price} = {subtotal} {currency}"
        ),
        "cart_total": (
            "Celkem bez dopravy: <b>{total} {currency}</b>"
        ),
        "checkout": "✅ Dokončit objednávku",
        "clear_cart": "🗑 Vyprázdnit košík",
        "cart_cleared": "Košík byl vyprázdněn.",
        "quantity_changed": "Množství bylo změněno.",
        "checkout_name": "Zadejte jméno příjemce:",
        "checkout_phone": (
            "Stisknutím tlačítka níže sdílejte "
            "své telefonní číslo:"
        ),
        "share_phone": "📱 Sdílet moje číslo",
        "checkout_address": (
            "Zadejte doručovací adresu:"
        ),
        "choose_delivery": (
            "Vyberte způsob dopravy:"
        ),
        "choose_payment": "Vyberte způsob platby:",
        "zasilkovna": (
            "📦 Zásilkovna — {price} {currency}"
        ),
        "dhl": "🚚 DHL — {price} {currency}",
        "pickup": "🏠 Osobní odběr — zdarma",
        "cash": "💵 Hotově",
        "qr": "📱 QR převod",
        "confirm_order": (
            "Zkontrolujte objednávku:\n\n"
            "👤 {name}\n"
            "☎️ {phone}\n"
            "📍 {address}\n"
            "🚚 {delivery}\n"
            "💳 {payment}\n\n"
            "Produkty: {products_total} {currency}\n"
            "Doprava: {delivery_price} {currency}\n"
            "<b>Celkem: {total} {currency}</b>"
        ),
        "confirm": "✅ Potvrdit",
        "order_created": (
            "✅ Objednávka <b>č. {order_id}</b> "
            "byla vytvořena.\n"
            "Částka: <b>{total} {currency}</b>"
        ),
        "order_failed": (
            "Objednávku se nepodařilo vytvořit."
        ),
        "my_orders_empty": (
            "Zatím nemáte žádné objednávky."
        ),
        "contacts_text": (
            "☎️ <b>Beauty Shop</b>\n\n"
            "S dotazy k objednávce kontaktujte správce."
        ),
        "unknown": "Použijte tlačítka nabídky.",
        "admin_only": (
            "Tento příkaz je dostupný pouze správci."
        ),
        "invalid_name": (
            "Zadejte platné jméno, alespoň 2 znaky."
        ),
        "invalid_phone": (
            "Stiskněte tlačítko „Sdílet moje číslo“."
        ),
        "invalid_address": (
            "Zadejte úplnou doručovací adresu."
        ),
        "checkout_cancelled": (
            "Objednávka byla zrušena."
        ),
        "checkout_data_lost": (
            "Údaje byly ztraceny. Začněte znovu."
        ),
        "cart_changed": (
            "Obsah košíku se změnil nebo není dostatek "
            "zboží. Zkontrolujte košík."
        ),
        "delivery_zasilkovna": "Zásilkovna",
        "delivery_dhl": "DHL",
        "delivery_pickup": "Osobní odběr",
        "payment_cash": "Hotově",
        "payment_qr": "QR převod",
        "order_status": "Stav: {status}",
        "payment_status": "Platba: {status}",
        "order_summary": (
            "📦 <b>Objednávka č. {order_id}</b>\n"
            "Částka: <b>{total} {currency}</b>\n"
            "Stav: {status}\n"
            "Platba: {payment_status}"
        ),
        "payment_qr_instructions": (
            "📱 <b>Platba objednávky "
            "č. {order_id}</b>\n\n"
            "Příjemce: <b>{recipient}</b>\n"
            "IBAN: <code>{iban}</code>\n"
            "Částka: <b>{total} {currency}</b>\n"
            "Variabilní symbol: "
            "<code>{variable_symbol}</code>\n\n"
            "Po zaplacení stiskněte tlačítko níže."
        ),
        "payment_qr_not_configured": (
            "Objednávka byla vytvořena, ale IBAN není "
            "nastaven. Správce vás bude kontaktovat."
        ),
        "payment_sent": "✅ Zaplatil/a jsem",
        "payment_check_requested": (
            "✅ Žádost o kontrolu platby byla "
            "odeslána správci."
        ),
        "payment_check_failed": (
            "Žádost nelze odeslat. "
            "Možná již byla odeslána."
        ),
        "pickup_info": (
            "🏠 <b>Osobní odběr</b>\n\n"
            "📍 Adresa: {address}\n"
            "🕐 Výdejní doba: {hours}"
        ),
        "back_delivery": "⬅️ Změnit dopravu",
        "contacts_text": (
            "📞 <b>Kontakty</b>\n\n"
            "Telefon: <a href=\"tel:+420608888151\">"
            "+420 608 888 151</a>\n"
            "Instagram: "
            "<a href=\"https://instagram.com/natalia_siedunova_hairdresser\">"
            "@natalia_siedunova_hairdresser</a>"
        ),
    },
    "uk": {
        "language_title": "🌐 Виберіть мову:",
        "language_saved": "✅ Мову змінено.",
        "welcome": (
            "🧴 <b>Ласкаво просимо до Beauty Shop!</b>"
            "\n\nВиберіть потрібний розділ:"
        ),
        "main_menu": "🏠 Головне меню",
        "catalog": "🛍 Каталог",
        "cart": "🛒 Кошик",
        "orders": "📦 Мої замовлення",
        "language": "🌐 Мова",
        "contacts": "☎️ Контакти",
        "back": "⬅️ Назад",
        "cancel": "❌ Скасувати",
        "categories_title": "🗂 Виберіть категорію:",
        "category_empty": (
            "У цій категорії поки немає товарів."
        ),
        "catalog_empty": "Каталог поки порожній.",
        "product_price": "Ціна: <b>{price} {currency}</b>",
        "choose_volume": "Виберіть об’єм:",
        "product_variants": "Доступні об’єми:",
        "out_of_stock": "Немає в наявності",
        "add_to_cart": "➕ До кошика",
        "added_to_cart": "✅ Товар додано до кошика.",
        "add_failed": (
            "Не вдалося додати товар. "
            "Можливо, його немає в наявності."
        ),
        "cart_empty": "🛒 Ваш кошик порожній.",
        "cart_title": "🛒 <b>Ваш кошик</b>",
        "cart_item": (
            "• {name}\n"
            "  {quantity} × {price} = {subtotal} {currency}"
        ),
        "cart_total": (
            "Разом без доставки: <b>{total} {currency}</b>"
        ),
        "checkout": "✅ Оформити замовлення",
        "clear_cart": "🗑 Очистити кошик",
        "cart_cleared": "Кошик очищено.",
        "quantity_changed": "Кількість змінено.",
        "checkout_name": "Введіть ім’я отримувача:",
        "checkout_phone": (
            "Натисніть кнопку нижче, щоб поділитися "
            "своїм номером телефону:"
        ),
        "share_phone": "📱 Надіслати мій номер",
        "checkout_address": "Введіть адресу доставки:",
        "choose_delivery": (
            "Виберіть спосіб доставки:"
        ),
        "choose_payment": "Виберіть спосіб оплати:",
        "zasilkovna": (
            "📦 Zásilkovna — {price} {currency}"
        ),
        "dhl": "🚚 DHL — {price} {currency}",
        "pickup": "🏠 Самовивіз — безкоштовно",
        "cash": "💵 Готівкою",
        "qr": "📱 QR-переказ",
        "confirm_order": (
            "Перевірте замовлення:\n\n"
            "👤 {name}\n"
            "☎️ {phone}\n"
            "📍 {address}\n"
            "🚚 {delivery}\n"
            "💳 {payment}\n\n"
            "Товари: {products_total} {currency}\n"
            "Доставка: {delivery_price} {currency}\n"
            "<b>Разом: {total} {currency}</b>"
        ),
        "confirm": "✅ Підтвердити",
        "order_created": (
            "✅ Замовлення <b>№{order_id}</b> створено."
            "\nСума: <b>{total} {currency}</b>"
        ),
        "order_failed": (
            "Не вдалося створити замовлення."
        ),
        "my_orders_empty": (
            "У вас поки немає замовлень."
        ),
        "contacts_text": (
            "☎️ <b>Beauty Shop</b>\n\n"
            "З питань замовлення зв’яжіться "
            "з адміністратором."
        ),
        "unknown": "Використовуйте кнопки меню.",
        "admin_only": (
            "Ця команда доступна лише адміністратору."
        ),
        "invalid_name": (
            "Введіть коректне ім’я, "
            "щонайменше 2 символи."
        ),
        "invalid_phone": (
            "Натисніть кнопку «Надіслати мій номер»."
        ),
        "invalid_address": (
            "Введіть повну адресу доставки."
        ),
        "checkout_cancelled": (
            "Оформлення замовлення скасовано."
        ),
        "checkout_data_lost": (
            "Дані втрачено. "
            "Почніть оформлення заново."
        ),
        "cart_changed": (
            "Склад кошика змінився або товару "
            "недостатньо. Перевірте кошик."
        ),
        "delivery_zasilkovna": "Zásilkovna",
        "delivery_dhl": "DHL",
        "delivery_pickup": "Самовивіз",
        "payment_cash": "Готівкою",
        "payment_qr": "QR-переказ",
        "order_status": "Статус: {status}",
        "payment_status": "Оплата: {status}",
        "order_summary": (
            "📦 <b>Замовлення №{order_id}</b>\n"
            "Сума: <b>{total} {currency}</b>\n"
            "Статус: {status}\n"
            "Оплата: {payment_status}"
        ),
        "payment_qr_instructions": (
            "📱 <b>Оплата замовлення "
            "№{order_id}</b>\n\n"
            "Отримувач: <b>{recipient}</b>\n"
            "IBAN: <code>{iban}</code>\n"
            "Сума: <b>{total} {currency}</b>\n"
            "Змінний символ: "
            "<code>{variable_symbol}</code>\n\n"
            "Після оплати натисніть кнопку нижче."
        ),
        "payment_qr_not_configured": (
            "Замовлення створено, але IBAN ще не "
            "налаштовано. Адміністратор зв’яжеться "
            "з вами."
        ),
        "payment_sent": "✅ Я оплатив/ла",
        "payment_check_requested": (
            "✅ Запит на перевірку оплати надіслано "
            "адміністратору."
        ),
        "payment_check_failed": (
            "Не вдалося надіслати запит. "
            "Можливо, його вже надіслано."
        ),
        "pickup_info": (
            "🏠 <b>Самовивіз</b>\n\n"
            "📍 Адреса: {address}\n"
            "🕐 Час видачі: {hours}"
        ),
        "back_delivery": "⬅️ Змінити доставку",
        "contacts_text": (
            "📞 <b>Контакти</b>\n\n"
            "Телефон: <a href=\"tel:+420608888151\">"
            "+420 608 888 151</a>\n"
            "Instagram: "
            "<a href=\"https://instagram.com/natalia_siedunova_hairdresser\">"
            "@natalia_siedunova_hairdresser</a>"
        ),
    },
}


def normalize_language(
    language: str | None,
) -> str:
    value = str(language or "").strip().lower()

    return (
        value
        if value in SUPPORTED_LANGUAGES
        else DEFAULT_LANGUAGE
    )


def text(
    language: str | None,
    key: str,
    **values: Any,
) -> str:
    language = normalize_language(language)

    template = TEXTS.get(
        language,
        TEXTS[DEFAULT_LANGUAGE],
    ).get(key)

    if template is None:
        template = TEXTS[DEFAULT_LANGUAGE].get(
            key,
            key,
        )

    if not values:
        return template

    try:
        return template.format(**values)
    except (KeyError, ValueError) as error:
        logging.error(
            "Ошибка форматирования текста "
            "language=%s key=%s: %s",
            language,
            key,
            error,
        )
        return template


def localized_value(
    row: Any,
    field: str,
    language: str | None,
) -> str:
    language = normalize_language(language)

    try:
        value = row[f"{field}_{language}"]
    except (KeyError, IndexError, TypeError):
        value = None

    if not value:
        try:
            value = row[
                f"{field}_{DEFAULT_LANGUAGE}"
            ]
        except (KeyError, IndexError, TypeError):
            value = ""

    return str(value or "")
