from core.settings import settings

from .rabbitmq import rabbitmq


async def publish_event(event_name: str, data: dict):
    publish = await rabbitmq.publish_json(
        exchange_name=settings.RABBITMQ_MAIN_EXCHANGE,
        routing_key=event_name,
        data=data,
    )

    return publish
