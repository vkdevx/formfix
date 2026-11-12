from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.consent import router as consent_router
from app.api.privacy import router as privacy_router
from app.api.documents import router as documents_router
from app.api.review import router as review_router
from app.api.explanation import router as explanation_router
from app.api.admin import router as admin_router
from app.api.demo import router as demo_router

api_router = APIRouter()
api_router.include_router(auth_router)
api_router.include_router(consent_router)
api_router.include_router(privacy_router)
api_router.include_router(documents_router)
api_router.include_router(review_router)
api_router.include_router(explanation_router)
api_router.include_router(admin_router)
api_router.include_router(demo_router)

