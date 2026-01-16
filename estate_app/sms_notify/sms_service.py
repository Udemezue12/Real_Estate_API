import httpx
from core.settings import settings


class TermiiClient:
    def __init__(self):
        self.base_url = settings.TERMII_BASE_URL
        self.api_key = settings.TERMII_API_KEY
        self.client: httpx.AsyncClient | None = None

    async def connect(self):
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=10)
        print("Termii connected")

    async def close(self):
        if self.client:
            await self.client.aclose()
            print("Termii connection closed")

    async def ping(self):
        if not self.client:
            raise RuntimeError("Termii client not connected")

        try:
            test_payload = {
                "to": "2340000000000",
                "from": settings.TERMII_SENDER_ID,
                "sms": "Ping test",
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }
            response = await self.client.post("/api/sms/send", json=test_payload)
            if response.status_code == 200:
                print("Termii API ping successful!")
                return True
            else:
                print(
                    f"Termii API ping returned {response.status_code}:",
                    response.json(),
                )
                return False
        except Exception as e:
            print("Termii ping error:", e)
            return False

    async def send_sms(
        self,
        to: str,
        otp: str | None = None,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        if not message:
            if name:
                message = (
                    f"Hello {name}, your OTP is {otp}. "
                    "This code expires in 5 minutes. Do not share it with anyone."
                )
            else:
                message = (
                    f"Your OTP is {otp}. "
                    "This code expires in 5 minutes. Do not share it with anyone."
                )

        payload = {
            "to": to,
            "from": sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": self.api_key,
        }

        if not self.client:
            raise RuntimeError("Termii client not connected")

        response = await self.client.post("/api/sms/send", json=payload)
        return response.json()

    async def send_rent_reminder_sms(
        self,
        to: str,
        days_left: int,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        if not message:
            if name:
                message = (
                    f"Hello {name}, Your rent will expire in {days_left} day(s).\n\n"
                    "Please ensure your rent is renewed on time."
                )
            else:
                message = (
                    f"Your rent will expire in {days_left} day(s).\n\n"
                    "Please ensure your rent is renewed on time."
                )

        payload = {
            "to": to,
            "from": sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": self.api_key,
        }

        if not self.client:
            raise RuntimeError("Termii client not connected")

        response = await self.client.post("/api/sms/send", json=payload)
        return response.json()

    async def send_rent_expired_sms(
        self,
        to: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        if not message:
            if name:
                message = (
                    f"Hello{name}, Your rent has expired.\n\n"
                    "Please renew your rent immediately"
                )
            else:
                message = "Your rent has expired.\n\nPlease renew your rent immediately"

        payload = {
            "to": to,
            "from": sender_id,
            "sms": message,
            "type": "plain",
            "channel": "generic",
            "api_key": self.api_key,
        }

        if not self.client:
            raise RuntimeError("Termii client not connected")

        response = await self.client.post("/api/sms/send", json=payload)
        return response.json()


send_sms = TermiiClient()
