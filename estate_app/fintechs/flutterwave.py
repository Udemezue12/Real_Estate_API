import uuid
from decimal import Decimal
import httpx

from core.settings import settings


class FlutterwaveClient:
    BASE_URL = "https://api.flutterwave.com/v3"

    def __init__(self):
        self.secret = settings.FLUTTERWAVE_SECRET_KEY
        self.redirect_url = settings.REDIRECT_URL

        self.headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    async def initialize_payment(self, email: str, amount: Decimal):
        url = f"{self.BASE_URL}/payments"
        tx_ref = f"FLW-{uuid.uuid4().hex[:12]}"

        payload = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": "NGN",
            "redirect_url": self.redirect_url,
            "customer": {"email": email},
            "payment_options": "card",
            "customizations": {
                "title": "Rent Payment",
                "description": "House rent payment",
            },
        }

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, json=payload, headers=self.headers)

        res.raise_for_status()
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message"))

        return {
            "checkout_link": data["data"]["link"],
            "tx_ref": tx_ref,
        }

    async def verify_payment(self, tx_ref: str) -> dict:
        url = f"{self.BASE_URL}/transactions/verify_by_reference"

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.get(
                url,
                headers=self.headers,
                params={"tx_ref": tx_ref},
            )

        res.raise_for_status()
        payload = res.json()

        if payload.get("status") != "success":
            return {"success": False}

        tx = payload["data"]

        if tx["status"] != "successful":
            return {"success": False}

        return {
            "success": True,
            "tx_ref": tx["tx_ref"],
            "flw_ref": tx["flw_ref"],
            "amount": tx["amount"],
            "currency": tx["currency"],
            "paid_at": tx["created_at"],
            "customer": tx["customer"],
            "meta": tx.get("meta", {}),
        }

    async def transfer(
        self,
        *,
        amount: Decimal,
        account_number: str,
        bank_code: str,
        reference: str,
    ):
        url = f"{self.BASE_URL}/transfers"

        payload = {
            "account_bank": bank_code,
            "account_number": account_number,
            "amount": str(amount),
            "currency": "NGN",
            "debit_currency": "NGN",
            "narration": "Rent payout",
            "reference": reference,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                url,
                json=payload,
                headers=self.headers,
            )

        if res.status_code != 200:
            raise RuntimeError(f"Flutterwave error: {res.text}")
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message"))

        return {
            "provider": "flutterwave",
            "reference": data["data"]["reference"],
            "id": data["data"]["id"],
            "status": data["data"]["status"],
        }

    async def refund_payment(self, flw_ref: str):
        url = f"{self.BASE_URL}/transactions/{flw_ref}/refund"

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(url, headers=self.headers)

        res.raise_for_status()

        return res.json()

    async def get_banks(self):
        url = f"{self.BASE_URL}/banks/NG"

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(
                connect=45.0,  # 45 seconds to establish connection
                read=60.0,
                write=30.0,
                pool=60.0,
            )
        ) as client:
            res = await client.get(url, headers=self.headers)

        res.raise_for_status()

        return res.json()["data"]

    async def resolve_account(
        self,
        *,
        account_number: str,
        bank_code: str,
    ):
        url = f"{self.BASE_URL}/accounts/resolve"

        payload = {
            "account_number": account_number,
            "account_bank": bank_code,
        }

        async with httpx.AsyncClient(timeout=30) as client:
            res = await client.post(
                url,
                json=payload,
                headers=self.headers,
            )
        if res.status_code == 400:
            try:
                error_data = res.json()
            except Exception:
                error_data = res.text

            raise RuntimeError(f"Flutterwave 400 error: {error_data}")

        res.raise_for_status()
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message", "Account resolution failed"))

        return data["data"]
