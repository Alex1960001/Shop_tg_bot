from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def required_env(name: str) -> str:
    value = os.getenv(name, "").strip()

    if not value:
        raise RuntimeError(f"{name} не указан в .env")

    return value


def integer_env(
    name: str,
    default: int | None = None,
) -> int:
    raw_value = os.getenv(name, "").strip()

    if not raw_value:
        if default is None:
            raise RuntimeError(
                f"{name} не указан в .env"
            )
        return default

    try:
        value = int(raw_value)
    except ValueError as error:
        raise RuntimeError(
            f"{name} должен быть целым числом"
        ) from error

    if value < 0:
        raise RuntimeError(
            f"{name} не может быть отрицательным"
        )

    return value


def project_path(value: str) -> Path:
    path = Path(value).expanduser()

    if path.is_absolute():
        return path

    return BASE_DIR / path


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_id: int
    database_path: Path
    images_dir: Path
    qr_dir: Path
    currency: str
    zasilkovna_price: int
    dhl_price: int
    payment_iban: str
    payment_recipient: str
    payment_message_prefix: str


def load_settings() -> Settings:
    admin_id = integer_env("ADMIN_ID")

    if admin_id <= 0:
        raise RuntimeError(
            "ADMIN_ID должен быть больше нуля"
        )

    currency = (
        os.getenv("CURRENCY", "CZK")
        .strip()
        .upper()
        or "CZK"
    )

    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise RuntimeError(
            "CURRENCY должна содержать "
            "3 латинские буквы"
        )

    payment_iban = "".join(
        os.getenv("PAYMENT_IBAN", "").split()
    ).upper()

    if payment_iban and not re.fullmatch(
        r"[A-Z]{2}\d{2}[A-Z0-9]{11,30}",
        payment_iban,
    ):
        raise RuntimeError(
            "Некорректный PAYMENT_IBAN"
        )

    payment_recipient = (
        os.getenv(
            "PAYMENT_RECIPIENT",
            "Beauty Shop",
        ).strip()
        or "Beauty Shop"
    )

    payment_message_prefix = (
        os.getenv(
            "PAYMENT_MESSAGE_PREFIX",
            "Beauty Shop order",
        ).strip()
        or "Beauty Shop order"
    )

    loaded_settings = Settings(
        bot_token=required_env("BOT_TOKEN"),
        admin_id=admin_id,
        database_path=project_path(
            os.getenv(
                "DATABASE_PATH",
                "beauty_shop.db",
            )
        ),
        images_dir=project_path(
            os.getenv(
                "IMAGES_DIR",
                "images",
            )
        ),
        qr_dir=project_path(
            os.getenv(
                "QR_DIR",
                "qr_codes",
            )
        ),
        currency=currency,
        zasilkovna_price=integer_env(
            "ZASILKOVNA_PRICE",
            79,
        ),
        dhl_price=integer_env(
            "DHL_PRICE",
            149,
        ),
        payment_iban=payment_iban,
        payment_recipient=payment_recipient,
        payment_message_prefix=(
            payment_message_prefix
        ),
    )

    loaded_settings.images_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    loaded_settings.qr_dir.mkdir(
        parents=True,
        exist_ok=True,
    )
    loaded_settings.database_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    return loaded_settings


settings = load_settings()

SUPPORTED_LANGUAGES = ("ru", "cs", "uk")
DEFAULT_LANGUAGE = "ru"

DELIVERY_METHODS = {
    "zasilkovna": settings.zasilkovna_price,
    "dhl": settings.dhl_price,
    "pickup": 0,
}

PAYMENT_METHODS = {
    "cash",
    "qr",
}

ORDER_STATUSES = {
    "new",
    "accepted",
    "packed",
    "shipped",
    "completed",
    "cancelled",
}

ORDER_STATUS_TRANSITIONS = {
    "new": {
        "accepted",
        "cancelled",
    },
    "accepted": {
        "packed",
        "cancelled",
    },
    "packed": {
        "shipped",
        "cancelled",
    },
    "shipped": {
        "completed",
    },
    "completed": set(),
    "cancelled": set(),
}

PAYMENT_STATUSES = {
    "pending",
    "checking",
    "paid",
    "rejected",
}
