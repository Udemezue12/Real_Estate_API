
from decimal import Decimal

import httpx
from core.settings import settings


class PaystackClient:
    BASE_URL = "https://api.paystack.co"

    def __init__(self):
        self.secret = settings.PAYSTACK_SECRET_KEY
        self.headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    async def initialize_payment(
        self,
        *,
        email: str,
        amount: Decimal,
        reference: str,
        callback_url: str | None = None,
    ):
        url = f"{self.BASE_URL}/transaction/initialize"

        payload = {
            "email": email,
            "amount": int(amount * 100),
            "reference": reference,
        }

        if callback_url:
            payload["callback_url"] = callback_url

        async with httpx.AsyncClient() as client:
            res = await client.post(url, headers=self.headers, json=payload)

        res.raise_for_status()

        data = res.json()

        if not data.get("status"):
            raise RuntimeError(data.get("message", "Paystack init failed"))

        return data["data"]  

    async def verify_payment(self, reference: str):
        url = f"{self.BASE_URL}/transaction/verify/{reference}"

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=self.headers)

        res.raise_for_status()

        payload = res.json()

        if not payload.get("status"):
            return {"success": False}

        tx = payload["data"]

        
        if tx["status"] != "success":
            return {"success": False}

        return {
            "success": True,
            "status": tx["status"],          
            "reference": tx["reference"],
            "amount": tx["amount"] / 100,
            "currency": tx["currency"],
            "metadata": tx.get("metadata", {}),
            "paid_at": tx.get("paid_at"),
            "channel": tx.get("channel"),
            "customer": tx.get("customer"),
        }

    async def resolve_account(
        self,
        account_number: str,
        bank_code: str,
    ):
        url = f"{self.BASE_URL}/bank/resolve"

        params = {
            "account_number": account_number,
            "bank_code": bank_code,
        }

        async with httpx.AsyncClient() as client:
            res = await client.get(
                url,
                headers=self.headers,
                params=params,
            )

        data = res.json()

        if not data["status"]:
            raise RuntimeError(data["message"])

        return data["data"] 
    async def create_transfer_recipient(
        self,
        *,
        name: str,
        account_number: str,
        bank_code: str,
    ):
        url = f"{self.BASE_URL}/transferrecipient"

        payload = {
            "type": "nuban",
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": "NGN",
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)

        data = response.json()
        if not data["status"]:
            raise RuntimeError(data["message"])

        return data["data"]["recipient_code"]

    async def transfer(
        self,
        *,
        amount: Decimal,
        recipient_code: str,
        reference: str,
        reason: str = "Rent payout",
    ):
        url = f"{self.BASE_URL}/transfer"

        payload = {
            "source": "balance",
            "amount": int(amount * 100), 
            "recipient": recipient_code,
            "reference": reference,
            "reason": reason,
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)

        data = response.json()
        if not data["status"]:
            raise RuntimeError(data["message"])

        return {
            "provider": "paystack",
            "reference": data["data"]["reference"],
            "status": data["data"]["status"],
        }

    async def refund(self, reference: str):
        url = f"{self.BASE_URL}/refund"

        payload = {"transaction": reference}

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=self.headers, json=payload)

        data = response.json()
        if not data["status"]:
            raise RuntimeError(data["message"])

        return data["data"]
    async def get_banks(self):

        url = f"{self.BASE_URL}/bank"

        async with httpx.AsyncClient() as client:
            res = await client.get(url, headers=self.headers)

        res.raise_for_status()

        return res.json()["data"]
