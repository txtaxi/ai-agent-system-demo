from fastapi import APIRouter

from app.api.routes.agent_runs import router as agent_runs_router
from app.api.routes.chat import router as chat_router
from app.api.routes.conversations import router as conversations_router
from app.api.routes.documents import router as documents_router
from app.api.routes.feedback import router as feedback_router
from app.api.routes.health import router as health_router
from app.api.routes.knowledge_bases import router as knowledge_bases_router
from app.api.routes.retrieval import router as retrieval_router

api_router = APIRouter()
# 所有业务路由统一在这里汇总，main.py 只需要挂载一个 api_router。
api_router.include_router(health_router, tags=["health"])
api_router.include_router(knowledge_bases_router, tags=["knowledge-bases"])
api_router.include_router(documents_router, tags=["documents"])
api_router.include_router(retrieval_router, tags=["retrieval"])
api_router.include_router(chat_router, tags=["chat"])
api_router.include_router(conversations_router, tags=["conversations"])
api_router.include_router(agent_runs_router, tags=["agent-runs"])
api_router.include_router(feedback_router, tags=["feedback"])
