import httpx

from core.settings import settings


class TermiiClient:
    def __init__(self):
        self.base_url = settings.TERMII_BASE_URL
        self.api_key = settings.TERMII_API_KEY
        self.async_client: httpx.AsyncClient | None = None
        self.sync_client: httpx.Client | None = None

    def sync_connect(self):
        self.sync_client = httpx.Client(
            base_url=self.base_url,
            timeout=10,
        )

    def sync_close(self):
        if self.sync_client:
            self.sync_client.close()

    async def async_connect(self):
        self.async_client = httpx.AsyncClient(
            base_url=self.base_url, timeout=10)

    async def async_close(self):
        if self.async_client:
            await self.async_client.aclose()

    async def ping(self):
        if not self.async_client:
            raise RuntimeError("Termii client not connected")

    async def send_sms(
        self,
        to: str,
        otp: str | None = None,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
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

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    async def send_rent_reminder_sms(
        self,
        to: str,
        days_left: int,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
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

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    async def sync_send_rent_reminder_sms(
        self,
        to: str,
        days_left: int,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            self.sync_connect()
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

            if not self.sync_client:
                raise RuntimeError("Termii client not connected")

            response = self.sync_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            self.sync_close()

    async def send_rent_expired_sms(
        self,
        to: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
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

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    def sync_send_rent_expired_sms(
        self,
        to: str,
        message: str | None = None,
        name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            self.sync_connect()
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

            if not self.sync_client:
                raise RuntimeError("Termii client not connected")

            response = self.sync_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            self.async_close()

    async def send_tenant_rent_paid_sms(
        self,
        to: str,
        amount: str,
        message: str | None = None,
        tenant_name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
            if not message:
                if tenant_name:
                    message = (
                        f"Hello {tenant_name}, we have received your rent payment of {amount}.\n\n"
                        "Thank you for your prompt payment."
                    )
                else:
                    message = (
                        f"We have received your rent payment of {amount}.\n\n"
                        "Thank you for your prompt payment."
                    )

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }

            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()

    async def rent_paid_sms(
        self,
        to: str,
        amount: str,
        message: str | None = None,
        landlord_name: str | None = None,
        tenant_name: str | None = None,
        sender_id=settings.TERMII_SENDER_ID,
    ):
        try:
            await self.async_connect()
            if not message:
                if landlord_name:
                    message = (
                        f"Hello {landlord_name}, your tenant with the name {tenant_name} has paid rent of {amount}.\n\n"
                        "Thank you."
                    )
                else:
                    message = f"Your tenant has paid rent of {amount}.\n\nThank you."

            payload = {
                "to": to,
                "from": sender_id,
                "sms": message,
                "type": "plain",
                "channel": "generic",
                "api_key": self.api_key,
            }
            if not self.async_client:
                raise RuntimeError("Termii client not connected")

            response = await self.async_client.post("/api/sms/send", json=payload)
            return response.json()
        finally:
            await self.async_close()


send_sms = TermiiClient()
