from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    WebAppInfo,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

from .config import get_settings


def menu_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Murojaat yuborish")],
            [KeyboardButton(text="Murojaatlarim")],
            [KeyboardButton(text="Tugallangan murojaatlarim")],
            [KeyboardButton(text="Ishlatish bo‘yicha qo‘llanma")],
        ],
        resize_keyboard=True,
    )


def cancel_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True,
    )


def media_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Joylashuv yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
    )


def location_kb() -> ReplyKeyboardMarkup:
    webapp_url = get_settings().webapp_location_url
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(
                text="🗺 Xaritadan tanlash",
                web_app=WebAppInfo(url=webapp_url),
            )],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def confirm_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="✅ Yuborish")],
            [KeyboardButton(text="❌ Bekor qilish")],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


# ------------ Inline browse keyboards ------------

def reports_nav_kb(has_prev: bool, has_next: bool, can_resolve: bool) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    if has_prev:
        b.button(text="⬅️", callback_data="repnav:prev")

    b.button(text="📎 Fayllar", callback_data="repnav:files")

    if has_next:
        b.button(text="➡️", callback_data="repnav:next")

    b.adjust(3)

    if can_resolve:
        b.row(InlineKeyboardButton(text="✅ Hal bo‘ldi", callback_data="repnav:resolve"))

    b.row(InlineKeyboardButton(text="🔙 Menyuga", callback_data="repnav:menu"))
    return b.as_markup()


def resolve_confirm_kb() -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()
    b.button(text="✅ Tasdiqlayman", callback_data="represolve:yes")
    b.button(text="❌ Bekor", callback_data="represolve:no")
    b.adjust(2)
    return b.as_markup()


def files_list_kb(attachments_count: int) -> InlineKeyboardMarkup:
    b = InlineKeyboardBuilder()

    for i in range(attachments_count):
        b.button(text=f"📎 {i+1}", callback_data=f"repfile:{i}")

    b.adjust(4)

    b.row(
        InlineKeyboardButton(text="📤 Hammasini yuborish", callback_data="repfile:all"),
        InlineKeyboardButton(text="⬅️ Ortga", callback_data="repfile:back"),
    )
    return b.as_markup()


class OrgCb(CallbackData, prefix="org"):
    action: str          # "pick" | "page" | "cancel"
    page: int            # 1,2,3...
    org_id: str | None = None


def organizations_kb(orgs: list[dict], page: int, has_prev: bool, has_next: bool) -> InlineKeyboardMarkup:
    """
    orgs: [{"id": "...", "name": "..."}]
    """
    kb = InlineKeyboardBuilder()

    for org in orgs:
        kb.button(
            text=f"🏢 {org['name']}",
            callback_data=OrgCb(action="pick", page=page, org_id=str(org["id"])).pack()
        )

    nav = InlineKeyboardBuilder()
    if has_prev:
        nav.button(text="⬅️ Oldingi", callback_data=OrgCb(action="page", page=page - 1).pack())
    nav.button(text=f"📄 {page}", callback_data=OrgCb(action="noop", page=page).pack())
    if has_next:
        nav.button(text="Keyingi ➡️", callback_data=OrgCb(action="page", page=page + 1).pack())

    kb.adjust(1)  # har qatorda 1 tadan org
    kb.attach(nav)
    kb.button(text="❌ Bekor qilish", callback_data=OrgCb(action="cancel", page=page).pack())
    kb.adjust(1)

    return kb.as_markup()

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
