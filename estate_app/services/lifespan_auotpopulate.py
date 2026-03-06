
import logging

from core.get_db import AsyncSessionLocal

from services.bank_service import BankService
from services.lga_service import LGAService
from services.state_services import StateService

logger = logging.getLogger("autopopulate")

async def run_autopopulate():
    db = AsyncSessionLocal()
    try:
        
        try:
            await BankService(db).create()
        except Exception:
            await db.rollback()
        finally:
            await db.close()
    except Exception:
        logger.exception("Failed to update banks ")

    # try:
        
    #     try:

    #         await StateService(db).create_state()
    #     except Exception:
    #         await db.rollback()
    #     finally:
    #         await db.close()
    # except Exception:
    #     logger.exception("Failed to create or update states ")
    # try:
        
    #     try:
    #         await LGAService(db).create_lga()
    #     except Exception:
    #         await db.rollback()
    #     finally:
    #         await db.close()
    # except Exception:
    #     logger.exception("Failed to create or update LGA ")