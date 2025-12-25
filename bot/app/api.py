import aiohttp
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone
import json


class ApiError(Exception):
    pass


class ApiClient:
    """
    base_url misollar:
      - Agar backend URL lar /api/... bo'lsa:
          base_url = "http://127.0.0.1:8000/api"
        va bu class ichida endpointlar "/reports/", "/organizations/" bo'ladi (hozir sizda shunaqa).

      - Agar base_url = "http://127.0.0.1:8000" bo'lsa,
        unda endpointlar "/api/reports/" bo'lishi kerak.
    """
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    async def list_organizations(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        page: int = 1
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/organizations/?page={page}"
        headers = {"Authorization": f"Bearer {access_token}"}
        async with session.get(url, headers=headers) as r:
            if r.status == 401:
                raise ApiError("UNAUTHORIZED")
            if r.status != 200:
                # HTML kelib qolsa ham juda uzun bo‘lib ketmasin
                text = await r.text()
                raise ApiError(f"Organizations error: {r.status} {text[:500]}")
            return await r.json(content_type=None)

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
                raise ApiError(f"Auth error: {resp.status} {str(data)[:500]}")
            return data

    async def guide(self, session: aiohttp.ClientSession, access_token: str) -> Dict[str, Any]:
        url = f"{self.base_url}/guide/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Guide error: {resp.status} {str(data)[:500]}")
            return data

    async def my_reports(self, session: aiohttp.ClientSession, access_token: str, resolved: bool):
        url = f"{self.base_url}/reports/mine/resolved/" if resolved else f"{self.base_url}/reports/mine/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Reports error: {resp.status} {str(data)[:500]}")
            return data

    async def report_detail(self, session: aiohttp.ClientSession, access_token: str, report_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/reports/{report_id}/"
        async with session.get(url, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status != 200:
                raise ApiError(f"Report detail error: {resp.status} {str(data)[:500]}")
            return data

    async def resolve_report(self, session: aiohttp.ClientSession, access_token: str, report_id: str):
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
                raise ApiError(f"Resolve error: {resp.status} {str(data)[:500]}")
            return data

    async def create_report(
        self,
        session: aiohttp.ClientSession,
        access_token: str,
        description: str,
        latitude: float,
        longitude: float,
        organization_id: str,  # ✅ MUHIM: qo‘shildi
        files: List[Tuple[str, bytes, str]],  # (filename, content_bytes, content_type)
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/reports/"
        form = aiohttp.FormData()
        form.add_field("description", description)
        form.add_field("latitude", str(latitude))
        form.add_field("longitude", str(longitude))
        form.add_field("organization", str(organization_id))  # ✅ MUHIM

        for (filename, content, ctype) in files:
            form.add_field("files", content, filename=filename, content_type=ctype)

        async with session.post(url, data=form, headers={"Authorization": f"Bearer {access_token}"}) as resp:
            data = await resp.json(content_type=None)
            if resp.status == 401:
                raise ApiError("UNAUTHORIZED")
            if resp.status not in (200, 201):
                raise ApiError(f"Create report error: {resp.status} {str(data)[:500]}")
            return data


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()
