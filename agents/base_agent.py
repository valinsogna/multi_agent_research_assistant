"""
Classe base per tutti gli agenti del sistema.

Definisce l'interfaccia comune e la logica di comunicazione
con gli LLM locali (Ollama).
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

import sys
sys.path.append("..")
from config import get_llm_config, VERBOSE


# =============================================================================
# Data Classes per messaggi A2A
# =============================================================================

class MessageType(str, Enum):
    """Tipo di messaggio tra agenti."""
    REQUEST = "request"          # Richiesta di esecuzione task
    RESPONSE = "response"        # Risposta con risultati
    STATUS = "status"           # Aggiornamento stato
    ERROR = "error"             # Segnalazione errore
    HANDOFF = "handoff"         # Passaggio di contesto ad altro agente


@dataclass
class AgentMessage:
    """
    Messaggio scambiato tra agenti (protocollo A2A).
    
    Questo definisce la struttura di comunicazione inter-agente,
    permettendo collaborazione strutturata.
    """
    sender: str                          # ID agente mittente
    receiver: str                        # ID agente destinatario
    message_type: MessageType            # Tipo di messaggio
    content: Dict[str, Any]              # Payload del messaggio
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None # ID per tracciare conversazioni
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        """Serializza il messaggio."""
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value,
            "content": self.content,
            "timestamp": self.timestamp.isoformat(),
            "correlation_id": self.correlation_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "AgentMessage":
        """Deserializza un messaggio."""
        return cls(
            sender=data["sender"],
            receiver=data["receiver"],
            message_type=MessageType(data["message_type"]),
            content=data["content"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            correlation_id=data.get("correlation_id"),
            metadata=data.get("metadata", {})
        )


@dataclass
class AgentCapability:
    """Descrive una capacità di un agente."""
    name: str                    # Nome della capacità
    description: str             # Descrizione
    input_schema: Dict[str, Any] # Schema input atteso
    output_schema: Dict[str, Any] # Schema output prodotto


# =============================================================================
# Base Agent Class
# =============================================================================

class BaseAgent(ABC):
    """
    Classe base astratta per tutti gli agenti.
    
    Implementa:
    - Connessione a LLM (Ollama)
    - Protocollo di comunicazione A2A
    - Logging e debugging
    - Gestione errori
    """
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        system_prompt: str,
        model: Optional[str] = None
    ):
        """
        Inizializza l'agente.
        
        Args:
            agent_id: Identificativo univoco dell'agente
            name: Nome human-readable
            description: Descrizione del ruolo dell'agente
            system_prompt: Prompt di sistema per il LLM
            model: Nome modello Ollama (usa default da config se None)
        """
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        
        # Configurazione LLM
        llm_config = get_llm_config()
        self.model_name = model or llm_config["model"]
        
        # Inizializza LLM
        self.llm = ChatOllama(
            model=self.model_name,
            base_url=llm_config["base_url"],
            temperature=llm_config["temperature"]
        )
        
        # Stato interno
        self.message_history: List[AgentMessage] = []
        self.is_active = False
        self._capabilities: List[AgentCapability] = []
        
    # -------------------------------------------------------------------------
    # Abstract Methods (da implementare nelle sottoclassi)
    # -------------------------------------------------------------------------
    
    @abstractmethod
    async def process_request(
        self, 
        request: AgentMessage
    ) -> AgentMessage:
        """
        Processa una richiesta e restituisce una risposta.
        
        Ogni agente specializzato deve implementare questo metodo
        definendo la propria logica di elaborazione.
        
        Args:
            request: Messaggio di richiesta da elaborare
            
        Returns:
            Messaggio di risposta con risultati
        """
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[AgentCapability]:
        """
        Restituisce le capacità dell'agente.
        
        Usato per discovery e routing delle richieste.
        """
        pass
    
    # -------------------------------------------------------------------------
    # Core Methods
    # -------------------------------------------------------------------------
    
    async def invoke_llm(
        self,
        user_message: str,
        context: Optional[str] = None
    ) -> str:
        """
        Invoca il LLM con un messaggio.
        
        Args:
            user_message: Messaggio/domanda dell'utente
            context: Contesto aggiuntivo opzionale
            
        Returns:
            Risposta del LLM
        """
        messages = [
            SystemMessage(content=self.system_prompt)
        ]
        
        if context:
            messages.append(HumanMessage(content=f"Contesto:\n{context}"))
        
        messages.append(HumanMessage(content=user_message))
        
        if VERBOSE:
            print(f"[{self.name}] Invocando LLM...")
        
        try:
            response = await self.llm.ainvoke(messages)
            return response.content
        except Exception as e:
            error_msg = f"Errore LLM: {str(e)}"
            if VERBOSE:
                print(f"[{self.name}] {error_msg}")
            return error_msg
    
    def create_message(
        self,
        receiver: str,
        message_type: MessageType,
        content: Dict[str, Any],
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Crea un nuovo messaggio A2A.
        
        Args:
            receiver: ID agente destinatario
            message_type: Tipo di messaggio
            content: Contenuto del messaggio
            correlation_id: ID conversazione (opzionale)
            
        Returns:
            AgentMessage pronto per l'invio
        """
        message = AgentMessage(
            sender=self.agent_id,
            receiver=receiver,
            message_type=message_type,
            content=content,
            correlation_id=correlation_id,
            metadata={"agent_name": self.name}
        )
        
        # Salva nella history
        self.message_history.append(message)
        
        return message
    
    def create_response(
        self,
        original_request: AgentMessage,
        content: Dict[str, Any],
        success: bool = True
    ) -> AgentMessage:
        """
        Crea una risposta a una richiesta.
        
        Args:
            original_request: Richiesta originale
            content: Contenuto della risposta
            success: Se l'elaborazione è andata a buon fine
            
        Returns:
            AgentMessage di risposta
        """
        message_type = MessageType.RESPONSE if success else MessageType.ERROR
        
        return self.create_message(
            receiver=original_request.sender,
            message_type=message_type,
            content=content,
            correlation_id=original_request.correlation_id
        )
    
    def create_handoff(
        self,
        next_agent: str,
        context: Dict[str, Any],
        instructions: str,
        correlation_id: Optional[str] = None
    ) -> AgentMessage:
        """
        Crea un messaggio di handoff per passare il lavoro a un altro agente.
        
        Args:
            next_agent: ID dell'agente successivo
            context: Contesto accumulato
            instructions: Istruzioni per l'agente successivo
            correlation_id: ID conversazione
            
        Returns:
            AgentMessage di handoff
        """
        return self.create_message(
            receiver=next_agent,
            message_type=MessageType.HANDOFF,
            content={
                "context": context,
                "instructions": instructions,
                "previous_agent": self.agent_id
            },
            correlation_id=correlation_id
        )
    
    # -------------------------------------------------------------------------
    # Utility Methods
    # -------------------------------------------------------------------------
    
    def log(self, message: str, level: str = "INFO"):
        """Logging con prefisso agente."""
        if VERBOSE or level in ["ERROR", "WARNING"]:
            timestamp = datetime.now().strftime("%H:%M:%S")
            print(f"[{timestamp}] [{self.name}] [{level}] {message}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Restituisce statistiche dell'agente."""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "model": self.model_name,
            "messages_processed": len(self.message_history),
            "is_active": self.is_active,
            "capabilities": [c.name for c in self.get_capabilities()]
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.agent_id}, name={self.name})"


# =============================================================================
# Agent Registry (per discovery)
# =============================================================================

class AgentRegistry:
    """
    Registry per la scoperta e gestione degli agenti.
    
    Permette di:
    - Registrare agenti
    - Trovare agenti per capacità
    - Routing messaggi
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
    
    def register(self, agent: BaseAgent):
        """Registra un agente."""
        self._agents[agent.agent_id] = agent
        if VERBOSE:
            print(f"[Registry] Registrato agente: {agent.name}")
    
    def unregister(self, agent_id: str):
        """Rimuove un agente."""
        if agent_id in self._agents:
            del self._agents[agent_id]
    
    def get(self, agent_id: str) -> Optional[BaseAgent]:
        """Ottiene un agente per ID."""
        return self._agents.get(agent_id)
    
    def find_by_capability(self, capability_name: str) -> List[BaseAgent]:
        """Trova agenti che hanno una specifica capacità."""
        result = []
        for agent in self._agents.values():
            for cap in agent.get_capabilities():
                if cap.name == capability_name:
                    result.append(agent)
                    break
        return result
    
    def list_all(self) -> List[BaseAgent]:
        """Lista tutti gli agenti registrati."""
        return list(self._agents.values())
    
    async def route_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """
        Instrada un messaggio all'agente destinatario.
        
        Args:
            message: Messaggio da instradare
            
        Returns:
            Risposta dell'agente (se presente)
        """
        agent = self.get(message.receiver)
        if agent:
            return await agent.process_request(message)
        return None


# Singleton registry
_registry: Optional[AgentRegistry] = None

def get_registry() -> AgentRegistry:
    """Ottiene il registry singleton."""
    global _registry
    if _registry is None:
        _registry = AgentRegistry()
    return _registry
