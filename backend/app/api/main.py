from fastapi import APIRouter

from app.api.routes import games, utils

api_router = APIRouter()
api_router.include_router(games.router)
api_router.include_router(utils.router)
