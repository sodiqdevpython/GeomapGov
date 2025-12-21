import aiohttp
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone
import json


class ApiError(Exception):
    pass


class ApiClient:
    def __init__(self, base_url: str):
        self.base_url = base_url

    async def auth_telegram(
        self,
        session: aiohttp.ClientSession,
        telegram_id: int,
        first_name: str,
        last_name: str,
        phone_number: str,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/auth/telegram/"
        payload = {
            "telegram_id": telegram_id,
            "first_name": first_name,
            "last_name": last_name,
            "phone_number": phone_number,
        }
        async with session.post(url, json=payload) as resp:
            data = await resp.json(content_type=None)
            if resp.status != 200:
                raise ApiError(f"Auth error: {resp.status} {data}")
            return data

    async def guide(self, session: aiohttp.ClientSession, access_token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/guide/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Guide error: {resp.status} {data}")
            return data

    async def my_reports(self, session: aiohttp.ClientSession, access_token: str, resolved: bool):
        url = f"{self.base_url}/reports/mine/resolved/" if resolved else f"{self.base_url}/reports/mine/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Reports error: {resp.status} {data}")
            return data

    async def report_detail(self, session: aiohttp.ClientSession, access_token: str, report_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reports/{report_id}/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Report detail error: {resp.status} {data}")
            return data

    async def resolve_report(self, session, access_token: str, report_id: str):
        url = f"{self.base_url}/reports/{report_id}/resolve/"
        async with session.post(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            raw = await resp.text()

            # JSON bo'lmasa ham yiqilmasin
            try:
                data = json.loads(raw) if raw else {}
            except json.JSONDecodeError:
                data = {"detail": raw}

            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Resolve error: {resp.status} {data}")
            return data

    async def create_report(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        description: str,
        latitude: float,
        longitude: float,
        files: List[Tuple[str, bytes, str]],  # (filename, content_bytes, content_type)
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/reports/"
        form = aiohttp.FormData()
        form.add_field("description", description)
        form.add_field("latitude", str(latitude))
        form.add_field("longitude", str(longitude))

        for (filename, content, ctype) in files:
            form.add_field("files", content, filename=filename, content_type=ctype)

        async with session.post(url, data=form, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status not in (200, 201):
                raise ApiError(f"Create report error: {resp.status} {data}")
            return data


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
