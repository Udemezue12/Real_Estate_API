from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from core.email_breaker import email_breaker as breaker
from core.settings import settings
import smtplib


class EmailService:
    def sync_send(self, message: MIMEMultipart):
        async def smtp_operation():
            with smtplib.SMTP(
                host=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                timeout=5,
            ) as server:

                if settings.EMAIL_USE_TLS:
                    server.starttls()

                server.login(
                    settings.EMAIL_USER,
                    settings.EMAIL_PASSWORD,
                )

                server.send_message(message)

        return breaker.sync_call(smtp_operation)

    async def async_send(self, message):
        async def smtp_operation():
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                start_tls=settings.EMAIL_USE_TLS,
            )

        return await breaker.call(smtp_operation)

    def sync_send_refund_email(self, email: str, name: str, amount: str):
        html_content = f"""
      <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <h2 style="color: #d9534f;">Refund Confirmation</h2>

        <p>Dear {name},</p>

        <p>
            We would like to inform you that your recent payment of 
            <strong>{amount}</strong> has been successfully refunded.
        </p>

        <p>
            The refunded amount will reflect in your bank account or card 
            according to your financial institution's processing timeline.
        </p>

        <p>
            If you have any questions or require further assistance, 
            please contact our support team.
        </p>

        <p>
            Thank you for your patience and understanding.
        </p>

        <br>
        <p>Best regards,<br>
        <strong>Your Support Team</strong></p>
    </body>
    </html>
    """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Refund Confirmation Notice"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        self.sync_send(message=message)

    async def send_rent_paid_email(
        self, email: str, landlord_name: str, tenant_name: str, amount
    ):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Rent Payment Notification</h2>
            <p>Hello {landlord_name},</p>
            <p> {tenant_name} has paid rent of {amount}</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Expired Notice"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        await self.async_send(message=message)

    def sync_send_rent_paid_email(
        self, email: str, landlord_name: str, tenant_name: str, amount
    ):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Rent Payment Notification</h2>
            <p>Hello {landlord_name},</p>
            <p> {tenant_name} has paid rent of {amount}</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Expired Notice"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        self.sync_send(message=message)

    async def send_rent_reminder_email(self, email: str, days_left: int, name: str):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p>Your rent will expire in {days_left} day(s)</p>
            <p>Please ensure your rent is renewed on time</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Payment Reminder"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        await self.async_send(message)

    def sync_send_rent_reminder_email(self, email: str, days_left: int, name: str):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p>Your rent will expire in {days_left} day(s)</p>
            <p>Please ensure your rent is renewed on time</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Payment Reminder"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        self.sync_send(message)

    async def send_rent_expired_email(self, email: str, name: str):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p> "Your rent has expired</p>
            <p>Please renew your rent immediately"</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Expired Notice"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        await self.async_send(message)

    def sync_send_rent_expired_email(self, email: str, name: str):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p> "Your rent has expired</p>
            <p>Please renew your rent immediately"</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Expired Notice"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))

        self.sync_send(message)

    async def send_verification_email(
        self, email: str, otp: str, token: str, name: str
    ):

        verify_link = f"{settings.FRONTEND_URL}/verify-email?token={token}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello {name},</p>
            <p>Your one-time password (OTP) is:</p>
            <h3 style="color:#007bff;">{otp}</h3>
            <p>You can also verify your email by clicking the link below:</p>
            <a href="{verify_link}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Verify Email</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you did not request this, please ignore this message.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Verify Your Email"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))
        await self.async_send(message=message)

    async def send_password_reset_link(self, email: str, otp: str, token: str):

        reset_link = f"{settings.FRONTEND_URL}/reset-password?token={token}"

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Email Verification</h2>
            <p>Hello,</p>
            <p>Your one-time password (OTP) is:</p>
            <h3 style="color:#007bff;">{otp}</h3>
            <p>You can also verify your email by clicking the link below:</p>
            <a href="{reset_link}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Verify Email</a>
            <p>This link will expire in 1 hour.</p>
            <hr>
            <p>If you did not request this, please ignore this message.</p>
            <p>Best regards,<br>Your Support Team</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Reset Your Password"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))
        await self.async_send(message=message)

    async def send_rent_processed_mail(
        self, email: str, landlord_name: str, tenant_name: str, path: str
    ):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Rent Payment Successfully Processed</h2>
            <p>Hello {tenant_name},</p>
    
            <p>Your rent has been fully processed, click here to download your receipt:</p>
            <a href="{path}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Download Receipt</a>

            <p>Best regards,<br>{landlord_name}</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Payment Successfully Processed"

        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))
        await self.async_send(message=message)

    def sync_send_rent_processed_mail(
        self, email: str, landlord_name: str, tenant_name: str, path: str
    ):

        html_content = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <h2>Payment Successful</h2>
            <p>Hello {tenant_name},</p>
    
            <p>Your rent has been fully processed, click here to download your receipt:</p>
            <a href="{path}" style="display:inline-block;background:#28a745;color:white;padding:10px 20px;
               text-decoration:none;border-radius:4px;">Download Receipt</a>

            <p>Best regards,<br>{landlord_name}</p>
        </body>
        </html>
        """

        message = MIMEMultipart("alternative")
        message["Subject"] = "Rent Payment Successfully Processed"
        message["From"] = settings.EMAIL_USER
        message["To"] = email
        message.attach(MIMEText(html_content, "html"))
        self.sync_send(message=message)
