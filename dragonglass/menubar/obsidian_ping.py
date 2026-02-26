from __future__ import annotations

import httpx

_HTTP_ERROR_THRESHOLD = 500


async def is_obsidian_online(url: str, api_key: str) -> bool:
    try:
        async with httpx.AsyncClient(timeout=2.0, verify=False) as client:
            resp = await client.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            return resp.status_code < _HTTP_ERROR_THRESHOLD
    except Exception:
        return False
