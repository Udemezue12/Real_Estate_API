from typing import Dict

import httpx

from core.settings import settings


class PremblyNINVerifier:
    BASE_URL = "https://api.prembly.com/verification/vnin-basic"

    async def verify_nin(self, nin: str) -> Dict:
     

        headers = {
            "app-id": settings.PREMBLY_APP_ID,
            "x-api-key": settings.PREMBLY_API_KEY,
            "Content-Type": "application/json",
        }

        payload = {"number_nin": nin}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                self.BASE_URL,
                json=payload,
                headers=headers,
            )

        resp.raise_for_status()

        result = resp.json()

        if not result.get("status") or not result.get("nin_data"):
            print("Prembly NIN verification failed:", result.get("detail"))
            return {"verified": False, "raw_response": result}

        nin_data = result.get("nin_data", {})

        print("Prembly NIN verified successfully")

        return {
            "verified": True,
            "first_name": nin_data.get("firstname") or nin_data.get("first_name"),
            "last_name": nin_data.get("surname") or nin_data.get("last_name"),
        }
