import json

import aio_pika
from aio_pika import ExchangeType, Message
from .breaker import breaker
from .settings import settings
from tenacity import retry, stop_after_attempt, wait_exponential


class RabbitMQConnection:
    def __init__(self, url: str):
        self.url = url
        self.connection = None
        self.channel = None

    @retry(
        stop=stop_after_attempt(5), wait=wait_exponential(multiplier=2, min=2, max=10)
    )
    async def connect(self):
        try:
            if not self.connection or self.connection.is_closed:
                print("Connecting to RabbitMQ...")
                self.connection = await aio_pika.connect_robust(self.url)
                self.channel = await self.connection.channel()
                print("Connected to RabbitMQ.")
        except Exception as e:
            print(f"Failed to connect to RabbitMQ: {e}")
            raise

    async def declare_queue_with_dlq(self, queue_name: str):
        try:
            await self.connect()

            dlx = await self.channel.declare_exchange(
                settings.RABBITMQ_DLX, ExchangeType.DIRECT
            )
            dlq = await self.channel.declare_queue(
                settings.RABBITMQ_DLX_QUEUE, durable=True
            )
            await dlq.bind(dlx, routing_key=settings.RABBITMQ_DLX_QUEUE)

            main_exchange = await self.channel.declare_exchange(
                queue_name, ExchangeType.DIRECT
            )
            queue = await self.channel.declare_queue(
                queue_name,
                durable=True,
                arguments={
                    "x-dead-letter-exchange": settings.RABBITMQ_DLX,
                    "x-dead-letter-routing-key": settings.RABBITMQ_DLX_QUEUE,
                },
            )
            await queue.bind(main_exchange, routing_key=queue_name)

            print(
                f"Queue '{queue_name}' declared with DLQ '{settings.RABBITMQ_DLX_QUEUE}'."
            )
            return main_exchange, queue

        except Exception as e:
            print(f"Failed to declare queue '{queue_name}': {e}")

    async def publish_json(self, exchange_name: str, routing_key: str, data: dict):
        async def handler():
            try:
                await self.connect()
                exchange = await self.channel.get_exchange(exchange_name)
                message_body = json.dumps(data).encode()
                message = Message(body=message_body, content_type="application/json")
                await exchange.publish(message, routing_key=routing_key)
                print(f"Published message to {exchange_name}:{routing_key}")
            except Exception as e:
                print(f"Failed to publish message: {e}")

        await breaker.call(handler)

    async def consume_json(self, queue_name: str, callback):
        try:
            await self.connect()
            queue = await self.channel.get_queue(queue_name)

            async with queue.iterator() as queue_iter:
                async for message in queue_iter:
                    async with message.process():
                        try:
                            data = json.loads(message.body.decode())
                            await callback(data)
                        except Exception as e:
                            print(f"Error processing message: {e}")
        except Exception as e:
            print(f"Failed to consume messages from '{queue_name}': {e}")


rabbitmq = RabbitMQConnection(settings.RABBITMQ_URL)
