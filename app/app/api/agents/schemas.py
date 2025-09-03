# app/api/agents/schemas.py
"""
Schemas para conversação com agentes de desenvolvimento.
"""
from __future__ import annotations

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

from .types import AgentType, AgentCapability


# =========================
#   CHAT SCHEMAS
# =========================
class ChatMessage(BaseModel):
    """Mensagem individual no chat."""
    id: str
    role: Literal["user", "assistant", "system"]
    content: str
    timestamp: datetime
    metadata: Optional[Dict[str, Any]] = None


class ChatContext(BaseModel):
    """Contexto da conversa com o agente."""
    workspace_path: Optional[str] = None
    current_file: Optional[str] = None
    project_type: Optional[str] = None
    language: Optional[str] = None
    recent_files: List[str] = Field(default_factory=list)
    session_id: str


class ChatRequest(BaseModel):
    """Requisição para conversar com agente."""
    message: str = Field(..., description="Mensagem do usuário")
    agent_id: str = Field(..., description="ID do agente a ser usado")
    context: Optional[ChatContext] = None
    include_code_context: bool = Field(True, description="Incluir contexto do código atual")
    max_tokens: Optional[int] = Field(None, description="Limite de tokens na resposta")


class ChatResponse(BaseModel):
    """Resposta do agente."""
    message_id: str
    content: str
    agent_id: str
    agent_name: str
    timestamp: datetime
    suggestions: List[str] = Field(default_factory=list)
    code_blocks: List[Dict[str, str]] = Field(default_factory=list)
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Optional[Dict[str, Any]] = None


# =========================
#   AGENT MANAGEMENT
# =========================
class AgentInfo(BaseModel):
    """Informações sobre um agente."""
    id: str
    name: str
    type: AgentType
    description: str
    capabilities: List[AgentCapability]
    is_available: bool = True


class AgentListResponse(BaseModel):
    """Lista de agentes disponíveis."""
    agents: List[AgentInfo]
    total: int


# =========================
#   CODE GENERATION
# =========================
class CodeGenerationRequest(BaseModel):
    """Requisição para geração de código."""
    prompt: str = Field(..., description="Descrição do código a ser gerado")
    agent_id: str = Field(..., description="ID do agente gerador")
    language: str = Field("python", description="Linguagem de programação")
    context_files: List[str] = Field(default_factory=list, description="Arquivos de contexto")
    target_file: Optional[str] = Field(None, description="Arquivo de destino")
    include_tests: bool = Field(False, description="Incluir testes gerados")
    include_docs: bool = Field(False, description="Incluir documentação")


class CodeGenerationResponse(BaseModel):
    """Resposta da geração de código."""
    code: str
    language: str
    explanation: str
    tests: Optional[str] = None
    documentation: Optional[str] = None
    suggestions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =========================
#   CODE REVIEW
# =========================
class CodeReviewRequest(BaseModel):
    """Requisição para revisão de código."""
    file_path: str = Field(..., description="Caminho do arquivo a ser revisado")
    agent_id: str = Field("code_review", description="ID do agente revisor")
    focus_areas: List[str] = Field(default_factory=list, description="Áreas de foco (performance, security, etc)")
    include_suggestions: bool = Field(True, description="Incluir sugestões de melhoria")


class CodeReviewResponse(BaseModel):
    """Resposta da revisão de código."""
    file_path: str
    issues: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    score: Optional[float] = Field(None, description="Score de qualidade (0-10)")
    summary: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


# =========================
#   SESSION MANAGEMENT
# =========================
class ChatSession(BaseModel):
    """Sessão de chat com agente."""
    session_id: str
    agent_id: str
    user_id: str
    created_at: datetime
    last_activity: datetime
    messages: List[ChatMessage] = Field(default_factory=list)
    context: Optional[ChatContext] = None
    is_active: bool = True


class SessionListResponse(BaseModel):
    """Lista de sessões do usuário."""
    sessions: List[ChatSession]
    total: int

