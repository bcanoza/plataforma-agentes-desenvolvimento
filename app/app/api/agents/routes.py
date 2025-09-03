# app/api/agents/routes.py
"""
Rotas para conversação e gerenciamento de agentes de desenvolvimento.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.api.auth.dependencies import require_user, CurrentUser
from app.core.logging_config import get_logger

from .schemas import (
    ChatRequest, ChatResponse, AgentListResponse, AgentInfo,
    CodeGenerationRequest, CodeGenerationResponse,
    CodeReviewRequest, CodeReviewResponse,
    SessionListResponse, ChatSession, ChatContext
)
from .services import AgentService, CodeGenerationService, CodeReviewService, ChatService
from .types import AgentType, AgentCapability

logger = get_logger("agents")

# Router principal dos agentes
router = APIRouter(prefix="/v1/agents", tags=["Agents"])

# Serviços
agent_service = AgentService()
code_gen_service = CodeGenerationService(agent_service)
code_review_service = CodeReviewService(agent_service)
chat_service = ChatService(agent_service)


# =========================
#   AGENT MANAGEMENT
# =========================
@router.get("/", response_model=AgentListResponse)
async def list_agents(current: CurrentUser = Depends(require_user)):
    """Lista todos os agentes disponíveis."""
    agents = agent_service.get_available_agents()
    
    agent_infos = [
        AgentInfo(
            id=agent.id,
            name=agent.name,
            type=agent.type,
            description=agent.description,
            capabilities=agent.capabilities,
            is_available=True
        )
        for agent in agents
    ]
    
    return AgentListResponse(agents=agent_infos, total=len(agent_infos))


@router.get("/{agent_id}", response_model=AgentInfo)
async def get_agent(agent_id: str, current: CurrentUser = Depends(require_user)):
    """Retorna informações sobre um agente específico."""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    return AgentInfo(
        id=agent.id,
        name=agent.name,
        type=agent.type,
        description=agent.description,
        capabilities=agent.capabilities,
        is_available=True
    )


# =========================
#   CHAT SESSIONS
# =========================
@router.post("/sessions", response_model=ChatSession)
async def create_chat_session(
    agent_id: str,
    context: Optional[ChatContext] = None,
    current: CurrentUser = Depends(require_user)
):
    """Cria nova sessão de chat com agente."""
    agent = agent_service.get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agente não encontrado")
    
    session = agent_service.create_chat_session(
        user_id=current["sub"],
        agent_id=agent_id,
        context=context
    )
    
    logger.info(f"Chat session created: {session.session_id} with agent {agent_id}")
    return session


@router.get("/sessions", response_model=SessionListResponse)
async def list_user_sessions(current: CurrentUser = Depends(require_user)):
    """Lista sessões ativas do usuário."""
    sessions = agent_service.get_user_sessions(current["sub"])
    return SessionListResponse(sessions=sessions, total=len(sessions))


@router.get("/sessions/{session_id}", response_model=ChatSession)
async def get_session(session_id: str, current: CurrentUser = Depends(require_user)):
    """Retorna sessão de chat específica."""
    session = agent_service.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada")
    
    if session.user_id != current["sub"]:
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    return session


# =========================
#   CHAT MESSAGES
# =========================
@router.post("/chat", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current: CurrentUser = Depends(require_user)
):
    """Envia mensagem para agente e retorna resposta."""
    try:
        # Verifica se o agente existe
        agent = agent_service.get_agent(request.agent_id)
        if not agent:
            raise HTTPException(status_code=404, detail="Agente não encontrado")
        
        # Cria sessão se não especificada no contexto
        session_id = request.context.session_id if request.context else None
        if not session_id:
            session = agent_service.create_chat_session(
                user_id=current["sub"],
                agent_id=request.agent_id,
                context=request.context
            )
            session_id = session.session_id
        
        # Envia mensagem
        response = await chat_service.send_message(
            session_id=session_id,
            message=request.message,
            include_code_context=request.include_code_context
        )
        
        logger.info(f"Message sent to agent {request.agent_id}: {request.message[:50]}...")
        return response
        
    except Exception as e:
        logger.exception("Error sending message to agent")
        raise HTTPException(status_code=500, detail=str(e))


# =========================
#   CODE GENERATION
# =========================
@router.post("/generate-code", response_model=CodeGenerationResponse)
async def generate_code(
    request: CodeGenerationRequest,
    current: CurrentUser = Depends(require_user)
):
    """Gera código usando agente específico."""
    try:
        response = await code_gen_service.generate_code(
            prompt=request.prompt,
            agent_id=request.agent_id,
            language=request.language,
            context_files=request.context_files,
            target_file=request.target_file,
            include_tests=request.include_tests,
            include_docs=request.include_docs
        )
        
        logger.info(f"Code generated by agent {request.agent_id}")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error generating code")
        raise HTTPException(status_code=500, detail=str(e))


# =========================
#   CODE REVIEW
# =========================
@router.post("/review-code", response_model=CodeReviewResponse)
async def review_code(
    request: CodeReviewRequest,
    current: CurrentUser = Depends(require_user)
):
    """Revisa código usando agente específico."""
    try:
        response = await code_review_service.review_code(
            file_path=request.file_path,
            agent_id=request.agent_id,
            focus_areas=request.focus_areas,
            include_suggestions=request.include_suggestions
        )
        
        logger.info(f"Code reviewed by agent {request.agent_id}: {request.file_path}")
        return response
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception("Error reviewing code")
        raise HTTPException(status_code=500, detail=str(e))


# =========================
#   HEALTH CHECK
# =========================
@router.get("/health")
async def health_check():
    """Health check dos agentes."""
    return {
        "status": "ok",
        "agents_available": len(agent_service.get_available_agents()),
        "active_sessions": len(agent_service.active_sessions)
    }

