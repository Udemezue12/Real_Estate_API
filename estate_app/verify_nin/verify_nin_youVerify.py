from typing import Dict

import httpx

from core.settings import settings


class YouVerifyNin:
    async def verify_nin(self, nin: str) -> Dict:
        headers = {
            "Authorization": f"Bearer {settings.YOUVERIFY_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "id": nin,
            "isSubjectConsent": True,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.youverify.co/v2/identity/ng/nin",
                json=payload,
                headers=headers,
            )

        resp.raise_for_status()
        data = resp.json().get("data")

        if not data or not data.get("valid"):
            print("YouVerify NIN verification failed")
            return {"verified": False}

        print("YouVerify NIN verified successfully")

        return {
            "verified": True,
            "first_name": data.get("firstname") or data.get("first_name"),
            "last_name": data.get("surname") or data.get("last_name"),
        }
