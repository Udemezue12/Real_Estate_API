import uuid
from decimal import Decimal
import httpx
from core.settings import settings


class FlutterwaveClient:
    BASE_URL = "https://api.flutterwave.com/v3"

    def __init__(self):
        self.secret = settings.FLUTTERWAVE_SECRET_KEY

        self.headers = {
            "Authorization": f"Bearer {self.secret}",
            "Content-Type": "application/json",
        }

    def initialize_payment(
        self, email: str, amount: Decimal, reference: str, redirect_url: str
    ):
        url = f"{self.BASE_URL}/payments"

        payload = {
            "tx_ref": reference,
            "amount": str(amount),
            "currency": "NGN",
            "redirect_url": redirect_url,
            "customer": {"email": email},
            "payment_options": "card",
            "customizations": {
                "title": "Rent Online Payment",
                "description": "Online Payment for AutoPopulate Api",
            },
        }

        with httpx.Client(timeout=30) as client:
            res = client.post(url, json=payload, headers=self.headers)

        res.raise_for_status()
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message"))

        return {
            "checkout_link": data["data"]["link"],
            "tx_ref": reference,
        }

    def verify_payment(self, tx_ref: str):
        url = f"{self.BASE_URL}/transactions/verify_by_reference"

        with httpx.Client(timeout=30) as client:
            res = client.get(
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
            "transaction_id": tx["id"],

        }

    def transfer(
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

        with httpx.Client(timeout=30) as client:
            res = client.post(url, json=payload, headers=self.headers)

        res.raise_for_status()
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message"))

        return {
            "provider": "flutterwave",
            "reference": data["data"]["reference"],
            "id": data["data"]["id"],
            "status": data["data"]["status"],
        }

    def refund_payment(self, flw_ref: str):
        url = f"{self.BASE_URL}/transactions/{flw_ref}/refund"

        with httpx.Client(timeout=30) as client:
            res = client.post(url, headers=self.headers)

        res.raise_for_status()
        return res.json()

    def get_banks(self):
        url = f"{self.BASE_URL}/banks/NG"

        with httpx.Client(timeout=60) as client:
            res = client.get(url, headers=self.headers)

        res.raise_for_status()
        return res.json()["data"]

    def resolve_account(self, *, account_number: str, bank_code: str):
        url = f"{self.BASE_URL}/accounts/resolve"

        payload = {
            "account_number": account_number,
            "account_bank": bank_code,
        }

        with httpx.Client(timeout=30) as client:
            res = client.post(url, json=payload, headers=self.headers)

        if res.status_code == 400:
            raise RuntimeError(f"Flutterwave 400 error: {res.text}")

        res.raise_for_status()
        data = res.json()

        if data.get("status") != "success":
            raise RuntimeError(data.get("message", "Account resolution failed"))

        return data["data"]