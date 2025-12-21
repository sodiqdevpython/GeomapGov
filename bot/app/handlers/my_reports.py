import aiohttp
import html
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, URLInputFile
from aiogram.fsm.context import FSMContext

from ..db import BotDB
from ..api import ApiClient, ApiError, now_iso
from ..states import BrowseReports
from ..keyboards import menu_kb, reports_nav_kb, files_list_kb, resolve_confirm_kb

router = Router()


STATUS_TITLE = {
    "new": "🟥 Yangi",
    "in_progress": "🟨 Jarayonda",
    "resolved": "🟩 Hal qilindi",
    "rejected": "⬛ Rad etildi",
    "RESOLVED": "🟩 Hal qilindi",
}


def normalize_items(payload):
    if isinstance(payload, list):
        return payload, None
    if isinstance(payload, dict):
        if "results" in payload and isinstance(payload["results"], list):
            return payload["results"], None
        detail = payload.get("detail") or payload.get("message") or str(payload)
        return [], f"Server list qaytarmadi: {detail}"
    return [], f"Noto‘g‘ri format: {type(payload)}"


def short_id(uid: str) -> str:
    return (uid or "")[:8]


def maps_url(lat, lon) -> str:
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"


def humanize_seconds(sec: int) -> str:
    if sec < 0:
        sec = 0
    days = sec // 86400
    sec %= 86400
    hours = sec // 3600
    sec %= 3600
    mins = sec // 60
    parts = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    parts.append(f"{mins} daqiqa")
    return " ".join(parts)


def parse_dt(s: str) -> str:
    if not s:
        return ""
    s = s.replace("T", " ")
    return s[:19]


def format_report_card_html(r: dict, idx: int, total: int, resolved_list: bool) -> str:
    rid = r.get("id", "")
    status = r.get("status", "")
    created = parse_dt(r.get("created_at") or "")
    resolved_at = parse_dt(r.get("resolved_at") or "")
    desc = (r.get("description") or "").strip()
    if len(desc) > 600:
        desc = desc[:600] + "…"

    lat = r.get("latitude")
    lon = r.get("longitude")
    attachments = r.get("attachments") or []

    header = "📌 <b>Murojaat (Hal qilindi)</b>" if resolved_list else "📌 <b>Murojaat</b>"
    st = STATUS_TITLE.get(status, status)

    link = maps_url(lat, lon) if (lat is not None and lon is not None) else ""

    lines = [
        header,
        f"#{idx+1}/{total}  |  ID: <code>{html.escape(short_id(rid))}</code>",
        "",
        f"Holati: <b>{html.escape(str(st))}</b>",
        f"Yuborilgan: {html.escape(created)}" if created else "Yuborilgan: -",
    ]

    if resolved_at:
        lines.append(f"Hal bo‘lgan: {html.escape(resolved_at)}")

    if link:
        lines.append(f"🗺 <a href=\"{html.escape(link)}\">Xaritada ko‘rish</a>")

    lines.append(f"📎 Fayllar: <b>{len(attachments)}</b> ta")
    lines.append("")
    lines.append(f"📝 {html.escape(desc)}")

    return "\n".join(lines)


async def ensure_fresh_token(db: BotDB, api: ApiClient, telegram_id: int) -> str:
    user = await db.get_user(telegram_id)
    if not user:
        return ""

    async with aiohttp.ClientSession() as session:
        auth = await api.auth_telegram(
            session=session,
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


async def fetch_reports_with_refresh(message: Message, db: BotDB, api: ApiClient, resolved: bool):
    telegram_id = message.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        return None, "Avval /start qilib ro‘yxatdan o‘ting."

    async def fetch(access: str):
        async with aiohttp.ClientSession() as session:
            return await api.my_reports(session, access, resolved=resolved)

    try:
        payload = await fetch(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await ensure_fresh_token(db, api, telegram_id)
            payload = await fetch(new_access)
        else:
            return None, f"Xatolik: {e}"

    items, err = normalize_items(payload)
    if err:
        return None, err

    return items, None


async def show_current_report(message_or_query, state: FSMContext):
    data = await state.get_data()
    reports = data.get("reports") or []
    idx = int(data.get("idx", 0))
    resolved_list = bool(data.get("resolved", False))

    if not reports:
        if isinstance(message_or_query, CallbackQuery):
            await message_or_query.message.answer("Hozircha murojaat yo‘q.", reply_markup=menu_kb())
            await message_or_query.answer()
        else:
            await message_or_query.answer("Hozircha murojaat yo‘q.", reply_markup=menu_kb())
        await state.clear()
        return

    idx = max(0, min(idx, len(reports) - 1))
    await state.update_data(idx=idx)

    r = reports[idx]
    text = format_report_card_html(r, idx, len(reports), resolved_list=resolved_list)

    # resolved list bo‘lmasa va status resolved bo‘lmasa -> Hal bo‘ldi tugmasi chiqadi
    can_resolve = (not resolved_list) and (str(r.get("status")).lower() != "resolved")

    kb = reports_nav_kb(
        has_prev=idx > 0,
        has_next=idx < len(reports) - 1,
        can_resolve=can_resolve,
    )

    if isinstance(message_or_query, CallbackQuery):
        await message_or_query.message.edit_text(
            text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )
        await message_or_query.answer()
    else:
        await message_or_query.answer(
            text,
            reply_markup=kb,
            parse_mode="HTML",
            disable_web_page_preview=True,
        )


@router.message(F.text.startswith("2."))
async def my_reports(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    await state.clear()
    items, err = await fetch_reports_with_refresh(message, db, api, resolved=False)
    if err:
        await message.answer(f"❌ {err}", reply_markup=menu_kb())
        return
    if not items:
        await message.answer("Hozircha murojaatlaringiz yo‘q.", reply_markup=menu_kb())
        return

    await state.set_state(BrowseReports.browsing)
    await state.update_data(reports=items, idx=0, resolved=False)
    await show_current_report(message, state)


@router.message(F.text.startswith("3."))
async def my_resolved_reports(message: Message, state: FSMContext, db: BotDB, api: ApiClient):
    await state.clear()
    items, err = await fetch_reports_with_refresh(message, db, api, resolved=True)
    if err:
        await message.answer(f"❌ {err}", reply_markup=menu_kb())
        return
    if not items:
        await message.answer("Hal qilingan murojaatlaringiz hozircha yo‘q.", reply_markup=menu_kb())
        return

    await state.set_state(BrowseReports.browsing)
    await state.update_data(reports=items, idx=0, resolved=True)
    await show_current_report(message, state)


@router.callback_query(F.data.startswith("repnav:"))
async def repnav_handler(query: CallbackQuery, state: FSMContext):
    action = query.data.split(":", 1)[1]
    data = await state.get_data()

    if action == "menu":
        await state.clear()
        await query.message.answer("Menyu:", reply_markup=menu_kb())
        await query.answer()
        return

    reports = data.get("reports") or []
    if not reports:
        await state.clear()
        await query.message.answer("Hozircha murojaat yo‘q.", reply_markup=menu_kb())
        await query.answer()
        return

    idx = int(data.get("idx", 0))

    if action == "prev":
        await state.update_data(idx=max(0, idx - 1))
        await show_current_report(query, state)
        return

    if action == "next":
        await state.update_data(idx=min(len(reports) - 1, idx + 1))
        await show_current_report(query, state)
        return

    if action == "files":
        r = reports[idx]
        attachments = r.get("attachments") or []
        await state.set_state(BrowseReports.choosing_file)
        await state.update_data(current_report=r)

        if not attachments:
            await query.answer("Fayl yo‘q", show_alert=False)
            return

        await query.message.answer(
            f"📎 Fayllar ({len(attachments)} ta). Tanlang:",
            reply_markup=files_list_kb(len(attachments)),
        )
        await query.answer()
        return

    if action == "resolve":
        await query.message.answer(
            "✅ Ushbu murojaat to‘liq hal bo‘ldimi?\nTasdiqlasangiz status 'Hal qilindi' bo‘ladi.",
            reply_markup=resolve_confirm_kb(),
        )
        await query.answer()
        return

    await query.answer()


@router.callback_query(F.data.startswith("represolve:"))
async def represolve_handler(query: CallbackQuery, state: FSMContext, db: BotDB, api: ApiClient):
    action = query.data.split(":", 1)[1]
    if action == "no":
        await query.answer("Bekor qilindi")
        return

    telegram_id = query.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await query.message.answer("Avval /start qilib ro‘yxatdan o‘ting.", reply_markup=menu_kb())
        await query.answer()
        return

    data = await state.get_data()
    reports = data.get("reports") or []
    idx = int(data.get("idx", 0))
    resolved_list = bool(data.get("resolved", False))

    if not reports:
        await query.answer("Report topilmadi")
        return

    r = reports[idx]
    report_id = str(r.get("id"))

    async def do_resolve(access: str):
        async with aiohttp.ClientSession() as session:
            return await api.resolve_report(session, access, report_id)

    try:
        result = await do_resolve(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await ensure_fresh_token(db, api, telegram_id)
            result = await do_resolve(new_access)
        else:
            await query.message.answer(f"❌ Xatolik: {e}")
            await query.answer()
            return

    sec = int(result.get("resolution_seconds", 0))
    await query.message.answer(f"🙏 Rahmat! Murojaatingiz hal qilindi deb belgilandi.\n⏱ Hal bo‘lish vaqti: {humanize_seconds(sec)}")
    await query.answer("Tasdiqlandi")

    # “Murojaatlarim”dan olib tashlaymiz — user keyin “Hal qilindi”da ko‘radi
    if not resolved_list:
        reports.pop(idx)
        if idx >= len(reports):
            idx = max(0, len(reports) - 1)
        await state.update_data(reports=reports, idx=idx)
        await show_current_report(query, state)
    else:
        await show_current_report(query, state)


@router.callback_query(F.data.startswith("repfile:"))
async def repfile_handler(query: CallbackQuery, state: FSMContext, db: BotDB, api: ApiClient):
    telegram_id = query.from_user.id
    user = await db.get_user(telegram_id)
    if not user:
        await state.clear()
        await query.message.answer("Avval /start qilib ro‘yxatdan o‘ting.", reply_markup=menu_kb())
        await query.answer()
        return

    data = await state.get_data()
    r = data.get("current_report") or {}
    report_id = r.get("id")
    if not report_id:
        await query.answer("Report topilmadi", show_alert=False)
        return

    async def fetch_detail(access: str):
        async with aiohttp.ClientSession() as session:
            return await api.report_detail(session, access, str(report_id))

    try:
        detail = await fetch_detail(user["access_token"])
    except ApiError as e:
        if str(e) == "UNAUTHORIZED":
            new_access = await ensure_fresh_token(db, api, telegram_id)
            detail = await fetch_detail(new_access)
        else:
            await query.message.answer(f"❌ Xatolik: {e}")
            await query.answer()
            return

    attachments = detail.get("attachments") or []
    if not attachments:
        await query.answer("Fayl yo‘q", show_alert=False)
        return

    action = query.data.split(":", 1)[1]

    if action == "back":
        await state.set_state(BrowseReports.browsing)
        await query.answer("Ortga")
        return

    async def send_one(att: dict):
        f_url = att.get("file_url")
        if not f_url:
            return
        t = att.get("type")
        url_file = URLInputFile(f_url)

        if t == "image":
            await query.message.answer_photo(url_file)
        elif t == "video":
            await query.message.answer_video(url_file)
        elif t == "voice":
            try:
                await query.message.answer_voice(url_file)
            except Exception:
                await query.message.answer_document(url_file)
        else:
            await query.message.answer_document(url_file)

    if action == "all":
        await query.answer("Yuborilyapti…")
        for att in attachments[:10]:
            await send_one(att)
        if len(attachments) > 10:
            await query.message.answer(f"Yana {len(attachments)-10} ta fayl bor (keyin pagination qilamiz).")
        return

    try:
        file_idx = int(action)
    except ValueError:
        await query.answer()
        return

    if file_idx < 0 or file_idx >= len(attachments):
        await query.answer("Noto‘g‘ri tanlov", show_alert=False)
        return

    await query.answer("Yuborilyapti…")
    await send_one(attachments[file_idx])
