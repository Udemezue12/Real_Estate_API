🏢 Property Management & Sales System (FastAPI)

A scalable, asynchronous property management and real estate platform built with FastAPI, designed for property sales, rentals, tenant management, and secure payments.
The system integrates modern fintech, messaging, and infrastructure tools to deliver a reliable, production-ready solution.

📌 Overview

The Property Management & Sales System enables property owners, agents, and tenants to manage rentals and property sales efficiently.

It supports:

Property listing (sale & rent)

Tenant management

Secure online and offline payments

Automated receipt generation

Real-time messaging

Identity verification

Owner–tenant communication

High-performance distributed processing

The platform is designed using asynchronous architecture, microservice-friendly patterns, and fault-tolerant mechanisms.

🚀 Key Features
🏠 Property Management

Create and manage properties for sale or rent

Attach tenants to rental properties

Manage multiple tenants per property

Property-based tenant organization

👥 Tenant Management

Tenant registration and profile management

Property–tenant linking

Rent tracking

Tenant history records

💬 Real-Time Communication

WebSocket-based messaging

Separate channels for:

Sales inquiries

Rental communication

Real-time notifications

💳 Payment System

Supports both online and offline payments:

Online Payments

Paystack

Flutterwave

Offline Payments

Receipt upload

Admin/owner verification

Automated Processing

Payment validation

Rent receipt generation

Payment history tracking

Secure transaction logging

📄 Rent Receipt System

Automatic receipt generation after successful payment

Available for both online and offline payments

Stored and accessible to tenants and owners

✉️ Owner–Tenant Communication

Property owners can send:

Notices

Letters

Announcements

Messages can be sent per property or per tenant group

🧾 Identity & Profile Verification

To prevent fake accounts, the system supports:

Bank Account Verification

BVN Verification

NIN Verification

Integrated with fintech and verification services.

⚡ Performance & Reliability

Distributed task processing

Fault tolerance

Caching

Rate limiting

Circuit breaker implementation

Idempotency support

Geospatial querying

🛠️ Technology Stack
Backend

FastAPI (Async API Framework)

PostgreSQL (Async)

SQLAlchemy Async / asyncpg

WebSockets

Task & Messaging

RabbitMQ

Celery

Dramatiq

Storage & Media

Cloudinary (Media Storage)

Payments & Fintech

Paystack

Flutterwave

Termii (SMS/OTP)

Gmail SMTP

Infrastructure & Reliability

Redis Cache

Rate Limiting

Circuit Breaker

Idempotency

Retry Policies

Background Workers

📁 Project Structure
real-estate-project/
│
├── estate-app/
│   ├── core/          # Core configurations and settings
│   ├── models/        # Database models
│   ├── services/      # Business logic
│   ├── repos/         # Repository layer
│   ├── routes/        # API endpoints
│   ├── webhooks/      # Payment & event webhooks
│   ├── fintechs/      # Payment & verification integrations
│   ├── workers/       # Celery/Dramatiq tasks
│   ├── utils/         # Utilities and helpers
│   └── app.py        # Application entry point
│
├── migrations/
├── requirements.txt
├── docker-compose.yml
└── README.md

⚙️ System Architecture

API Layer → FastAPI (Async REST + WebSocket)

Service Layer → Business logic

Repository Layer → Database access

Task Workers → Celery & Dramatiq

Message Broker → RabbitMQ

Cache Layer → Redis

Storage → Cloudinary

Database → PostgreSQL (Async)

🔐 Security Features

JWT Authentication

Role-based Access Control (RBAC)

Rate Limiting

Request Validation

Idempotent APIs

Secure Payment Webhooks

Identity Verification (BVN/NIN)

Encrypted Credentials

🌍 Deployment

This project is designed for cloud deployment using:

Docker & Docker Compose

Nginx (optional)

PostgreSQL

Redis

RabbitMQ

It currently runs without a public domain address and can be deployed on:

VPS

Cloud VM

Private server

Container platforms

▶️ Installation
1. Clone Repository
git clone https://github.com/your-username/real-estate-project.git
cd real-estate-project

2. Create Virtual Environment
python -m venv venv
source venv/bin/activate

3. Install Dependencies
pip install -r requirements.txt

4. Configure Environment

Create a .env file:

DATABASE_URL=
REDIS_URL=
RABBITMQ_URL=
PAYSTACK_SECRET=
FLUTTERWAVE_SECRET=
CLOUDINARY_KEY=
TERMII_KEY=
EMAIL_HOST=

5. Run Migrations
alembic upgrade head

6. Start Server
uvicorn estate-app.main:app --reload

7. Start Workers
celery -A estate-app.workers worker -l info
dramatiq estate-app.workers

📡 API Documentation

After running the server:

Swagger UI:

/docs


ReDoc:

/redoc

📈 Use Cases

Real estate agencies

Property managers

Landlords

Rental platforms

Property marketplaces

Multi-tenant housing systems

🧩 System Capabilities

High concurrency handling

Distributed processing

Fault-tolerant payments

Scalable messaging

Real-time notifications

Financial compliance support

Audit logging

🛣️ Future Enhancements

Mobile app integration

AI-powered property valuation

Smart contract integration

Analytics dashboard

Advanced fraud detection

Multi-language support

👨‍💻 Author

Udemezue Uchechukwu
Backend Engineer | Python & Distributed Systems

📄 License

This project is proprietary and intended for private or commercial use.
All rights reserved.