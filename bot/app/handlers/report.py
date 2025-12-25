import os
import time
import asyncio
import aiohttp
from io import BytesIO

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove
from aiogram.fsm.context import FSMContext

from ..states import ReportCreate
from ..keyboards import menu_kb, cancel_kb, media_kb, location_kb, confirm_kb
from ..keyboards import organizations_kb, OrgCb
from ..db import BotDB
from ..api import ApiClient, ApiError, now_iso
from ..utils import guess_content_type, safe_filename
from .my_reports import maps_url

router = Router()

MAX_FILES = 10

# ✅ Siz xohlagandek 50MB
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "50"))
MAX_FILE_SIZE = MAX_FILE_SIZE_MB * 1024 * 1024

# ✅ Redis yo‘q bo‘lsa ham “auto clear” qilish uchun (ixtiyoriy)
FLOW_TTL_SECONDS = int(os.getenv("REPORT_FLOW_TTL_SECONDS", "3600"))  # default 1 soat

# har user uchun expiry task saqlaymiz (MemoryStorage + 1 process bo‘lsa yetarli)
_EXPIRY_TASKS: dict[tuple[int, int], asyncio.Task] = {}


def _init_media_state():
    # files: [{file_id, filename, content_type, size}]
    return {"files": []}


def _fmt_mb(n: int | None) -> str:
    if not isinstance(n, int):
        return "-"
    return f"{n / (1024 * 1024):.1f}MB"


def _append_file(state_files: list, file_id: str, filename: str, content_type: str, size: int | None):
    state_files.append({"file_id": file_id, "filename": filename, "content_type": content_type, "size": size})


def _too_big(size: int | None) -> bool:
    return isinstance(size, int) and size > MAX_FILE_SIZE


def _task_key(message: Message) -> tuple[int, int]:
    return (message.chat.id, message.from_user.id)


async def _expire_after(bot, chat_id: int, user_id: int, state: FSMContext, expires_at: float):
    # expires_at kelganda state hanuz shu flow bo‘lsa tozalaymiz
    delay = max(0.0, expires_at - time.time())
    await asyncio.sleep(delay)

    try:
        data = await state.get_data()
        cur_expires = data.get("expires_at")
        cur_user = data.get("telegram_id")
        # faqat shu user flow’iga tegishli bo‘lsa
        if cur_user == user_id and isinstance(cur_expires, (int, float)) and cur_expires == expires_at:
            await state.clear()
            await bot.send_message(
                chat_id,
                "⏳ Murojaatni yuborish vaqti tugadi. Iltimos qaytadan boshlang.",
                reply_markup=menu_kb()
            )
    except Exception:
        # bot restart / state yo‘q / network xatolari — jim
        pass


async def _touch_ttl(message: Message, state: FSMContext):
    # TTL yangilash (Redis yo‘q bo‘lsa ham)
    expires_at = time.time() + FLOW_TTL_SECONDS
    await state.update_data(expires_at=expires_at, telegram_id=message.from_user.id)

    key = _task_key(message)
    old = _EXPIRY_TASKS.get(key)
    if old and not old.done():
        old.cancel()

    _EXPIRY_TASKS[key] = asyncio.create_task(
        _expire_after(message.bot, message.chat.id, message.from_user.id, state, expires_at)
    )


async def _ensure_not_expired(message: Message, state: FSMContext) -> bool:
    data = await state.get_data()
    expires_at = data.get("expires_at")
    if isinstance(expires_at, (int, float)) and time.time() > expires_at:
        await state.clear()
        await message.answer(
            "⏳ Murojaat jarayoni eskirib ketdi. Qaytadan boshlang.",
            reply_markup=menu_kb()
        )
        return False
    return True


async def _refresh_tokens(db: BotDB, api: ApiClient, telegram_id: int, user: dict) -> str:
    async with aiohttp.ClientSession() as session2:
        auth = await api.auth_telegram(
            session=session2,
            telegram_id=telegram_id,
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone_number=user["phone_number"],
        )
    access = auth["tokens"]["access"]
    refresh = auth["tokens"]["refresh"]
    await db.upsert_user_tokens(
        telegram_id=telegram_id,
        first_name=user["first_name"],
        last_name=user["last_name"],
        phone_number=user["phone_number"],
        access_token=access,
        refresh_token=refresh,
        updated_at_iso=now_iso(),
    )
    return access


async def _load_org_page(message: Message, state: FSMContext, db: BotDB, api: ApiClient, page: int, edit_from: Message | None = None):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.", reply_markup=menu_kb())
        return

    async def fetch(access_token: str):
        async with aiohttp.ClientSession() as session:
            return await api.list_organizations(session=session, access_token=access_token, page=page)

    try:
        data = await fetch(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await _refresh_tokens(db, api, telegram_id, user)
            data = await fetch(new_access)
        else:
            await message.answer(f"❌ Tashkilotlar yuklanmadi: {e}", reply_markup=menu_kb())
            await state.clear()
            return

    results = data.get("results") or data.get("items") or data.get("data") or []
    has_next = bool(data.get("next"))
    has_prev = bool(data.get("previous"))

    orgs = []
    for o in results:
        orgs.append({
            "id": o.get("id"),
            "name": o.get("name") or o.get("title") or str(o.get("id")),
        })

    await state.update_data(org_page=page)

    text = "🏢 Muammo qaysi tashkilotga tegishli? Tanlang:"

    kb = organizations_kb(orgs=orgs, page=page, has_prev=has_prev, has_next=has_next)

    if edit_from:
        try:
            await edit_from.edit_text(text, reply_markup=kb)
        except Exception:
            await message.answer(text, reply_markup=kb)
    else:
        await message.answer(text, reply_markup=kb)


@router.message(F.text.startswith("Murojaat yuborish"))
async def report_start(message: Message, state: FSMContext, db: BotDB):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    await state.clear()
    await state.set_state(ReportCreate.waiting_description)
    await state.update_data(media=_init_media_state())
    await _touch_ttl(message, state)

    await message.answer("Muammoni matn ko‘rinishida yozing:", reply_markup=cancel_kb())


@router.message(ReportCreate.waiting_description, F.text == "❌ Bekor qilish")
async def cancel_from_description(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.waiting_description, F.text)
async def report_got_description(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    text = (message.text or "").strip()
    if len(text) < 5:
        await message.answer("Matn juda qisqa. Iltimos muammoni batafsilroq yozing.", reply_markup=cancel_kb())
        return

    await state.update_data(description=text)
    await state.set_state(ReportCreate.collecting_media)

    await message.answer(
        "Endi xohlasangiz rasm/video/ovoz/audio/pdf/file yuboring.\n"
        "Tayyor bo‘lsangiz: ✅ Joylashuv yuborish ni bosing.\n\n",
        reply_markup=media_kb()
    )


@router.message(ReportCreate.collecting_media, F.text == "❌ Bekor qilish")
async def report_cancel_media(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.collecting_media, F.text == "✅ Joylashuv yuborish")
async def report_ask_location(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    await state.set_state(ReportCreate.waiting_location)
    await message.answer("Muammo joylashuvini yuboring.", reply_markup=location_kb())


async def _reject_big(message: Message, size: int | None):
    await message.answer(
        f"❌ Fayl qabul qilinmadi.\n"
        f"Maksimal: {MAX_FILE_SIZE_MB}MB\n"
        f"Siz yuborgan: {_fmt_mb(size)}\n\n"
        f"Iltimos kichikroq fayl yuboring.",
        reply_markup=media_kb()
    )


@router.message(ReportCreate.collecting_media, F.photo)
async def report_collect_photo(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    photo = message.photo[-1]
    size = getattr(photo, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    _append_file(files, photo.file_id, safe_filename(f"photo_{len(files)+1}.jpg"), "image/jpeg", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Rasm qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.video)
async def report_collect_video(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.video
    size = getattr(v, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(v.file_name or f"video_{len(files)+1}.mp4")
    _append_file(files, v.file_id, filename, v.mime_type or "video/mp4", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Video qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.voice)
async def report_collect_voice(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    v = message.voice
    size = getattr(v, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    _append_file(files, v.file_id, safe_filename(f"voice_{len(files)+1}.ogg"), v.mime_type or "audio/ogg", size)
    await state.update_data(media=media)
    await message.answer(f"✅ Ovozli xabar qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.audio)
async def report_collect_audio(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    a = message.audio
    size = getattr(a, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(a.file_name or f"audio_{len(files)+1}.mp3")
    _append_file(files, a.file_id, filename, a.mime_type or guess_content_type(filename), size)
    await state.update_data(media=media)
    await message.answer(f"✅ Audio qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.collecting_media, F.document)
async def report_collect_document(message: Message, state: FSMContext):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    data = await state.get_data()
    media = data.get("media") or _init_media_state()
    files = media["files"]

    if len(files) >= MAX_FILES:
        await message.answer(f"❌ Maksimal {MAX_FILES} ta fayl yuborish mumkin.", reply_markup=media_kb())
        return

    d = message.document
    size = getattr(d, "file_size", None)
    if _too_big(size):
        await _reject_big(message, size)
        return

    filename = safe_filename(d.file_name or f"file_{len(files)+1}")
    _append_file(files, d.file_id, filename, d.mime_type or guess_content_type(filename), size)
    await state.update_data(media=media)
    await message.answer(f"✅ Fayl qo‘shildi ({len(files)}/{MAX_FILES}).", reply_markup=media_kb())


@router.message(ReportCreate.waiting_location, F.text == "❌ Bekor qilish")
async def report_cancel_location(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())


@router.message(ReportCreate.waiting_location, F.location)
async def report_after_location_ask_org(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    lat = float(message.location.latitude)
    lon = float(message.location.longitude)
    await state.update_data(latitude=lat, longitude=lon)

    link = maps_url(lat, lon) if (lat is not None and lon is not None) else ""
    await state.set_state(ReportCreate.waiting_organization)

    await message.answer(
        f"📍 Joylashuv qabul qilindi: {link}\n\nEndi tashkilotni tanlang:",
        reply_markup=ReplyKeyboardRemove()
    )

    await _load_org_page(message, state, db, api, page=1)


@router.callback_query(ReportCreate.waiting_organization, OrgCb.filter())
async def org_pick_or_page(call: CallbackQuery, callback_data: OrgCb, state: FSMContext, db: BotDB, api: ApiClient):
    # TTL tekshiruv
    msg = call.message
    if not await _ensure_not_expired(msg, state):
        await call.answer()
        return
    await _touch_ttl(msg, state)

    action = callback_data.action
    page = int(callback_data.page or 1)

    if action == "cancel":
        await state.clear()
        await msg.answer("❌ Murojaat bekor qilindi.", reply_markup=menu_kb())
        await call.answer()
        return

    if action == "page":
        await call.answer()
        await _load_org_page(msg, state, db, api, page=page, edit_from=msg)
        return

    if action == "pick":
        org_id = callback_data.org_id
        if not org_id:
            await call.answer("Xatolik: org_id yo‘q", show_alert=True)
            return

        await state.update_data(organization_id=org_id)
        await call.answer("✅ Tashkilot tanlandi")

        data = await state.get_data()
        files = (data.get("media") or _init_media_state())["files"]
        lat = float(data.get("latitude"))
        lon = float(data.get("longitude"))
        link = maps_url(lat, lon)

        preview_text = (
            "📄 Murojaatni tasdiqlash\n\n"
            f"📝 Matn:\n{data.get('description','')}\n\n"
            f"📎 Fayllar soni: {len(files)}\n"
            f"📍 Joylashuv: {link}\n"
            f"🏢 Organization: {org_id}\n\n"
            "Agar hammasi to‘g‘ri bo‘lsa: ✅ Yuborish\n"
            "Aks holda: ❌ Bekor qilish"
        )

        await state.set_state(ReportCreate.confirm)
        await msg.answer(preview_text, reply_markup=confirm_kb())
        return

    await call.answer()


@router.message(ReportCreate.confirm, F.text == "❌ Bekor qilish")
async def report_cancel_confirm(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Murojaat bekor qilindi. Saqlanmadi.", reply_markup=menu_kb())


@router.message(ReportCreate.confirm, F.text == "✅ Yuborish")
async def report_submit_confirmed(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    if not await _ensure_not_expired(message, state):
        return
    await _touch_ttl(message, state)

    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await message.answer("Avval /start qilib ro‘yxatdan o‘ting.")
        return

    data = await state.get_data()
    description = data.get("description", "")
    lat = float(data.get("latitude"))
    lon = float(data.get("longitude"))
    organization_id = data.get("organization_id")

    if not organization_id:
        await state.clear()
        await message.answer("❌ Tashkilot tanlanmagan. Qaytadan urinib ko‘ring.", reply_markup=menu_kb())
        return

    files_meta = (data.get("media") or _init_media_state())["files"]

    await message.answer("⏳ Yuborilyapti… iltimos biroz kuting.")

    tg_files = []
    for item in files_meta:
        file_id = item["file_id"]
        filename = item["filename"]
        ctype = item["content_type"]
        size = item.get("size")

        # yana bir marta tekshiruv
        if _too_big(size):
            await message.answer(
                f"❌ {filename} qabul qilinmadi. ({_fmt_mb(size)})\nMaks: {MAX_FILE_SIZE_MB}MB",
                reply_markup=menu_kb()
            )
            await state.clear()
            return

        f = await message.bot.get_file(file_id)

        # get_file dan ham file_size chiqishi mumkin — yana tekshiramiz
        f_size = getattr(f, "file_size", None)
        if _too_big(f_size):
            await message.answer(
                f"❌ {filename} juda katta. ({_fmt_mb(f_size)})\nMaks: {MAX_FILE_SIZE_MB}MB",
                reply_markup=menu_kb()
            )
            await state.clear()
            return

        stream = BytesIO()
        await message.bot.download_file(f.file_path, stream)
        tg_files.append((filename, stream.getvalue(), ctype))

    async def submit(access_token: str):
        async with aiohttp.ClientSession() as session:
            return await api.create_report(
                session=session,
                access_token=access_token,
                description=description,
                latitude=lat,
                longitude=lon,
                organization_id=organization_id,
                files=tg_files,
            )

    try:
        created = await submit(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await _refresh_tokens(db, api, telegram_id, user)
            created = await submit(new_access)
        else:
            await message.answer(f"❌ Murojaat yuborilmadi: {e}", reply_markup=menu_kb())
            await state.clear()
            return

    await state.clear()
    await message.answer(
        f"✅ Murojaat saqlandi!\nID: {created.get('id')}\nStatus: {created.get('status')}",
        reply_markup=menu_kb()
    )
