from pydantic import BaseModel


class PaginatePage:
    def paginate(self, items: list, page: int, per_page: int):
        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]

    def get_list_json_dumps(self, paginated_props):
        return [p.model_dump(mode="json") for p in paginated_props]

    def get_list_dumps(self, paginated_props):
        return [p.model_dump() for p in paginated_props]

    def get_single_json_dumps(self, prop_dict):
        return prop_dict.model_dump(mode="json")

    async def serialize_response(self,schema: BaseModel) -> dict:
        return schema.model_dump()
    async def serialize_json_response(self,schema: BaseModel) -> dict:
        return schema.model_dump(mode="json")
