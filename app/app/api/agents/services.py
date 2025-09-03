# app/api/agents/services.py
"""
Serviços para gerenciamento e execução de agentes de desenvolvimento.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

from .types import AgentProfile, AGENTS
from .schemas import (
    ChatMessage, ChatContext, ChatResponse, CodeGenerationResponse,
    CodeReviewResponse, ChatSession
)


class AgentService:
    """Serviço principal para gerenciamento de agentes."""
    
    def __init__(self):
        self.agents = AGENTS
        self.active_sessions: Dict[str, ChatSession] = {}
    
    def get_available_agents(self) -> List[AgentProfile]:
        """Retorna lista de agentes disponíveis."""
        return list(self.agents.values())
    
    def get_agent(self, agent_id: str) -> Optional[AgentProfile]:
        """Retorna perfil de um agente específico."""
        return self.agents.get(agent_id)
    
    def create_chat_session(self, user_id: str, agent_id: str, context: Optional[ChatContext] = None) -> ChatSession:
        """Cria nova sessão de chat com agente."""
        session_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        session = ChatSession(
            session_id=session_id,
            agent_id=agent_id,
            user_id=user_id,
            created_at=now,
            last_activity=now,
            context=context
        )
        
        self.active_sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Retorna sessão de chat."""
        return self.active_sessions.get(session_id)
    
    def add_message_to_session(self, session_id: str, message: ChatMessage) -> bool:
        """Adiciona mensagem à sessão."""
        session = self.active_sessions.get(session_id)
        if not session:
            return False
        
        session.messages.append(message)
        session.last_activity = datetime.utcnow()
        return True
    
    def get_user_sessions(self, user_id: str) -> List[ChatSession]:
        """Retorna sessões ativas do usuário."""
        return [
            session for session in self.active_sessions.values()
            if session.user_id == user_id and session.is_active
        ]


class CodeGenerationService:
    """Serviço para geração de código pelos agentes."""
    
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service
    
    async def generate_code(
        self,
        prompt: str,
        agent_id: str,
        language: str = "python",
        context_files: List[str] = None,
        target_file: Optional[str] = None,
        include_tests: bool = False,
        include_docs: bool = False
    ) -> CodeGenerationResponse:
        """Gera código usando agente específico."""
        
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agente {agent_id} não encontrado")
        
        # TODO: Integrar com OpenAI
        # Por enquanto, retorna resposta mock
        return CodeGenerationResponse(
            code="# Código gerado pelo agente\nprint('Hello, World!')",
            language=language,
            explanation="Este é um exemplo de código gerado pelo agente.",
            tests="# Testes gerados\nassert True" if include_tests else None,
            documentation="# Documentação gerada" if include_docs else None,
            suggestions=["Considere adicionar tratamento de erros", "Use type hints"],
            metadata={"agent_id": agent_id, "generated_at": datetime.utcnow().isoformat()}
        )


class CodeReviewService:
    """Serviço para revisão de código pelos agentes."""
    
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service
    
    async def review_code(
        self,
        file_path: str,
        agent_id: str = "code_review",
        focus_areas: List[str] = None,
        include_suggestions: bool = True
    ) -> CodeReviewResponse:
        """Revisa código usando agente específico."""
        
        agent = self.agent_service.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agente {agent_id} não encontrado")
        
        # TODO: Integrar com OpenAI e ler arquivo
        # Por enquanto, retorna resposta mock
        return CodeReviewResponse(
            file_path=file_path,
            issues=[
                {
                    "type": "warning",
                    "line": 10,
                    "message": "Variável não utilizada",
                    "severity": "medium"
                }
            ],
            suggestions=[
                {
                    "type": "improvement",
                    "description": "Considere usar type hints",
                    "example": "def function(param: str) -> int:"
                }
            ],
            score=8.5,
            summary="Código bem estruturado com algumas oportunidades de melhoria.",
            metadata={"agent_id": agent_id, "reviewed_at": datetime.utcnow().isoformat()}
        )


class ChatService:
    """Serviço para conversação com agentes."""
    
    def __init__(self, agent_service: AgentService):
        self.agent_service = agent_service
    
    async def send_message(
        self,
        session_id: str,
        message: str,
        include_code_context: bool = True
    ) -> ChatResponse:
        """Envia mensagem para agente e retorna resposta."""
        
        session = self.agent_service.get_session(session_id)
        if not session:
            raise ValueError(f"Sessão {session_id} não encontrada")
        
        agent = self.agent_service.get_agent(session.agent_id)
        if not agent:
            raise ValueError(f"Agente {session.agent_id} não encontrado")
        
        # Adiciona mensagem do usuário à sessão
        user_message = ChatMessage(
            id=str(uuid.uuid4()),
            role="user",
            content=message,
            timestamp=datetime.utcnow()
        )
        self.agent_service.add_message_to_session(session_id, user_message)
        
        # TODO: Integrar com OpenAI
        # Por enquanto, retorna resposta mock
        response = ChatResponse(
            message_id=str(uuid.uuid4()),
            content=f"Entendi sua solicitação: '{message}'. Como posso ajudá-lo com o desenvolvimento?",
            agent_id=agent.id,
            agent_name=agent.name,
            timestamp=datetime.utcnow(),
            suggestions=[
                "Posso gerar código para você",
                "Posso revisar código existente",
                "Posso ajudar com debugging",
                "Posso criar testes"
            ],
            code_blocks=[],
            actions=[],
            metadata={"session_id": session_id}
        )
        
        # Adiciona resposta do agente à sessão
        agent_message = ChatMessage(
            id=response.message_id,
            role="assistant",
            content=response.content,
            timestamp=response.timestamp,
            metadata=response.metadata
        )
        self.agent_service.add_message_to_session(session_id, agent_message)
        
        return response

