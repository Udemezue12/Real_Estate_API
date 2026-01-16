from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib
from core.breaker import breaker
from core.settings import settings


async def send_rent_reminder_email(email: str, days_left: int, name: str):
    async def handler():
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

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                start_tls=settings.EMAIL_USE_TLS,
            )
        except Exception as e:
            print(f"Error sending rent reminder email: {e}")
            raise

    return await breaker.call(handler)


async def send_rent_expired_email(email: str, name: str):
    async def handler():
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

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                start_tls=settings.EMAIL_USE_TLS,
            )
        except Exception as e:
            print(f"Error sending email: {e}")
            raise

    return await breaker.call(handler)


async def send_verification_email(email: str, otp: str, token: str, name: str):
    async def handler():
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

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                start_tls=settings.EMAIL_USE_TLS,
            )
        except Exception as e:
            print(f"Error sending verification email: {e}")
            raise

    return await breaker.call(handler)


async def send_password_reset_link(email: str, otp: str, token: str):
    async def handler():
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

        try:
            await aiosmtplib.send(
                message,
                hostname=settings.EMAIL_SERVER,
                port=settings.EMAIL_PORT,
                username=settings.EMAIL_USER,
                password=settings.EMAIL_PASSWORD,
                start_tls=settings.EMAIL_USE_TLS,
            )
        except Exception as e:
            print(f"Error sending verification email: {e}")
            raise

    return await breaker.call(handler)
