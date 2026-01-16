from core.settings import settings
from typing import Dict
import httpx


class QoreIDVerifyyNin:
    async def verify_nin(
        self,
        nin: str,
    ) -> Dict:
        headers = {
            "Authorization": f"Bearer {settings.QOREID_API_KEY}",
            "Content-Type": "application/json",
        }

        payload = {
            "nin": nin,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.qoreid.com/v1/identity/nin",
                json=payload,
                headers=headers,
            )

        resp.raise_for_status()
        data = resp.json()

        if data.get("verificationStatus") != "verified":
            print("QoreID NIN verification failed")
            return {"verified": False}

        print("QoreID NIN verified successfully")

        return {
            "verified": True,
            "first_name": data.get("firstName"),
            "last_name": data.get("lastName"),
        }


qore = QoreIDVerifyyNin()