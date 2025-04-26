from fastapi import APIRouter

crud_router_v1 = APIRouter(prefix="/resource", tags=["resources"])

@crud_router_v1.get("/resource/{name}", description="Our first get endpoint.")
async def get_resource(name: str):
    return f"You gave me {name}"

