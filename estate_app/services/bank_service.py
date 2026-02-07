import logging

from core.cache import cache
from core.mapper import ORMMapper
from core.normalizer import get_canonical_bank_name
from core.paginate import PaginatePage
from core.redis_idempotency import RedisIdempotency
from fintechs.flutterwave import FlutterwaveClient
from fintechs.paystack import PaystackClient
from repos.bank_repo import BankRepo
from schemas.schema import BankOut

logger = logging.getLogger(__name__)


class BankService:
    LOCK_KEY: str = "bank-sync-v2"

    def __init__(self, db):
        self.db = db
        self.repo: BankRepo = BankRepo(db)
        self.paystack = PaystackClient()
        self.paginate: PaginatePage = PaginatePage()
        self.mapper: ORMMapper = ORMMapper()
        self.flutterwave = FlutterwaveClient()

        self.idempotency = RedisIdempotency(namespace="bank-service-startup")

    async def create(self):
        async def _sync():
            # if not await self.repo.needs_sync():
            #     logger.info("Bank sync skipped (already complete)")
            #     return

            logger.info("Starting bank sync...")

            paystack_banks = await self.paystack.get_banks()
            flutterwave_banks = await self.flutterwave.get_banks()

            flutter_map: dict[str, str] = {
                get_canonical_bank_name(b["name"]): b["code"] for b in flutterwave_banks
            }

            for bank in paystack_banks:
                raw_name = bank["name"].strip()
                canonical = get_canonical_bank_name(raw_name)

                flutter_code = flutter_map.get(canonical)

                await self.repo.create_or_update(
                    name=raw_name,
                    canonical_name=canonical,
                    paystack_bank_code=bank["code"],
                    flutterwave_bank_code=flutter_code,
                )

            logger.info("Bank sync completed successfully")
            await cache.delete_cache_keys_async("banks:all")

        await self.idempotency.run_once(
            key=self.LOCK_KEY,
            coro=_sync,
            ttl=120,
        )

    async def get_banks(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> list[BankOut]:
        cache_key = f"banks:all:{page}::{per_page}"

        cached = await cache.get_json(cache_key)
        if cached:
            return self.mapper.many(items=cached, schema=BankOut)
        listings = await self.repo.get_banks()
        listings_out = self.mapper.many(items=listings, schema=BankOut)
        paginated = self.paginate.paginate(listings_out, page, per_page)

        await cache.set_json(
            cache_key,
            self.paginate.get_list_json_dumps(paginated),
            ttl=300,
        )
        return paginated

    async def get_all_banks(
        self,
    ) -> list[BankOut]:
        cache_key = "banks::get"

        cached = await cache.get_json(cache_key)
        if cached:
            return [BankOut(**item) for item in cached]

        banks = await self.repo.get_all_banks()
        banks_out = self.mapper.many(items=banks, schema=BankOut)

        await cache.set_json(
            cache_key,
            [bank.model_dump(mode="json") for bank in banks_out],
            ttl=300,
        )

        return banks_out
