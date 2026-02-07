import uuid

from fastapi import HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload

from models.models import State


class StateRepo:
    def __init__(self, db):
        self.db = db

    async def get_all(self, page: int = 1, per_page: int = 20):
        result = await self.db.execute(
            select(State)
            .options(selectinload(State.lgas))
            .order_by(State.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def get_id(self, state_id: uuid.UUID):
        result = await self.db.execute(select(State).where(State.id == state_id))
        state = result.scalar_one_or_none()
        if not state:
            raise HTTPException(status_code=404, detail="State not found")
        return state

    async def get_name(self, name: str) -> State | None:
        result = await self.db.execute(select(State).where(State.name == name))
        return result.scalar_one_or_none()

    async def get_by_location(self, location) -> State | None:
        result = await self.db.execute(select(State).where(State.location == location))
        return result.scalar_one_or_none()
    

    async def create_or_get(self, *, name: str, geom) -> tuple[State, bool]:
        
        
       
        state = await self.get_name(name)
        

        try:
            if state:
                return state, False

            state = State(name=name,location=geom)
            self.db.add(state)

            await self.db.commit()
            await self.db.refresh(state)

            return state, True

        except SQLAlchemyError:
            await self.db.rollback()
            raise

    # async def create(self, name: str):
    #     point = await geocode_address(name)
    #     geom = from_shape(point, srid=4326)
    #     existing = await self.db.execute(select(State).where(State.location == geom))
    #     existing_state = existing.scalars().first()
    #     if existing_state:
    #         raise HTTPException(
    #             status_code=400, detail="The State has already been created"
    #         )
    #     state = State(name=name, location=geom)
    #     self.db.add(state)
    #     try:
    #         await self.db.commit()
    #         await self.db.refresh(state)
    #         return state
    #     except SQLAlchemyError:
    #         await self.db.rollback()
    #         raise HTTPException(status_code=500, detail="Failed to create state")

    async def get_all_states(self, page: int = 1, per_page: int = 20) -> list[State]:
        result = await self.db.execute(
            select(State)
            .order_by(State.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        return result.scalars().all()

    async def update_one(
        self, state_id: uuid.UUID, new_name: str | None = None
    ) -> State:
        state = await self.get_id(state_id)

        if new_name:
            state.name = new_name

            # point = await geocode_address(new_name)
            # state.location = from_shape(point, srid=4326)

        try:
            await self.db.commit()
            await self.db.refresh(state)
            return state

        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update state")

    async def update_all(self, new_name: str):
        stmt = (
            update(State)
            .values(name=new_name)
            .execution_options(synchronize_session=False)
        )

        try:
            await self.db.execute(stmt)
            await self.db.commit()

        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to update all states")

    async def delete_one(self, name: str) -> State:
        state = await self.get_name(name=name)
        await self.db.delete(state)

        try:
            await self.db.commit()
            return state

        except SQLAlchemyError as exc:
            await self.db.rollback()
            raise HTTPException(
                status_code=500, detail="Failed to delete state"
            ) from exc

    async def delete_all(self):
        stmt = delete(State)

        try:
            await self.db.execute(stmt)
            await self.db.commit()
            return {"message": "All states deleted"}

        except SQLAlchemyError:
            await self.db.rollback()
            raise HTTPException(status_code=500, detail="Failed to delete all states")

    async def get_one(self, name: str):
        result = await self.db.execute(
            select(State).where(State.name == name).options(selectinload(State.lgas))
        )

        state = result.scalar_one_or_none()
        if not state:
            return None
        return state.as_dict()

    async def get_all_with_lgas(self, page: int = 1, per_page: int = 20):
        result = await self.db.execute(
            select(State)
            .options(selectinload(State.lgas))
            .order_by(State.name)
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        states = result.scalars().all()
        return [state.as_dict() for state in states]
    async def db_commit(self):
        try:
            await self.db.commit()

        except SQLAlchemyError:
            await self.db.rollback()
            raise