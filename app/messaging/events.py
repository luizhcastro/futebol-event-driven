"""
Schemas de eventos e funções auxiliares para serialização/deserialização
"""

from dataclasses import dataclass, asdict
from typing import Dict, Any, List, Optional
from datetime import datetime


@dataclass
class JogoEvent:
    """Evento de jogo"""
    id_jogo: int
    time1: str
    time2: str
    data: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'JogoEvent':
        return JogoEvent(
            id_jogo=data['id_jogo'],
            time1=data['time1'],
            time2=data['time2'],
            data=data['data']
        )


@dataclass
class ComentarioEvent:
    """Evento de comentário"""
    id_jogo: int
    autor: str
    comentario: str
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'ComentarioEvent':
        return ComentarioEvent(
            id_jogo=data['id_jogo'],
            autor=data['autor'],
            comentario=data['comentario'],
            timestamp=data.get('timestamp')
        )


@dataclass
class VotoEvent:
    """Evento de voto"""
    id_jogo: int
    autor: str
    voto: str
    timestamp: Optional[str] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'VotoEvent':
        return VotoEvent(
            id_jogo=data['id_jogo'],
            autor=data['autor'],
            voto=data['voto'],
            timestamp=data.get('timestamp')
        )


@dataclass
class QueryEvent:
    """Evento de consulta (RPC)"""
    request_id: str
    id_jogo: Optional[int] = None
    filters: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'QueryEvent':
        return QueryEvent(
            request_id=data['request_id'],
            id_jogo=data.get('id_jogo'),
            filters=data.get('filters')
        )


# Constantes de eventos
class EventTypes:
    """Tipos de eventos no sistema"""

    # Comandos
    JOGO_CRIAR = 'jogo.criar'
    COMENTARIO_CRIAR = 'comentario.criar'
    VOTO_CRIAR = 'voto.criar'

    # Domain Events
    JOGO_REGISTRADO = 'jogo.registrado'
    COMENTARIO_REGISTRADO = 'comentario.registrado'
    VOTO_REGISTRADO = 'voto.registrado'

    # Queries
    QUERY_JOGOS = 'query.jogos'
    QUERY_COMENTARIOS = 'query.comentarios'
    QUERY_VOTACAO = 'query.votacao'


# Constantes de exchanges
class Exchanges:
    """Exchanges do RabbitMQ"""
    COMMANDS = 'futebol.commands'
    QUERIES = 'futebol.queries'
    EVENTS = 'futebol.events'


# Constantes de filas
class Queues:
    """Filas do RabbitMQ"""

    # Comandos
    JOGOS_COMMAND_CRIAR = 'jogos.command.criar'
    COMENTARIOS_COMMAND_CRIAR = 'comentarios.command.criar'
    VOTACAO_COMMAND_CRIAR = 'votacao.command.criar'

    # Queries
    JOGOS_QUERY_LISTAR = 'jogos.query.listar'
    COMENTARIOS_QUERY_LISTAR = 'comentarios.query.listar'
    VOTACAO_QUERY_LISTAR = 'votacao.query.listar'

    # Events
    COMENTARIOS_EVENTS_JOGO = 'comentarios.events.jogo'
    VOTACAO_EVENTS_JOGO = 'votacao.events.jogo'


def create_jogo_event(id_jogo: int, time1: str, time2: str, data: str) -> Dict[str, Any]:
    """Helper para criar evento de jogo"""
    event = JogoEvent(id_jogo=id_jogo, time1=time1, time2=time2, data=data)
    return event.to_dict()


def create_comentario_event(id_jogo: int, autor: str, comentario: str) -> Dict[str, Any]:
    """Helper para criar evento de comentário"""
    event = ComentarioEvent(id_jogo=id_jogo, autor=autor, comentario=comentario)
    return event.to_dict()


def create_voto_event(id_jogo: int, autor: str, voto: str) -> Dict[str, Any]:
    """Helper para criar evento de voto"""
    event = VotoEvent(id_jogo=id_jogo, autor=autor, voto=voto)
    return event.to_dict()


def create_query_event(request_id: str, id_jogo: Optional[int] = None) -> Dict[str, Any]:
    """Helper para criar evento de consulta"""
    event = QueryEvent(request_id=request_id, id_jogo=id_jogo)
    return event.to_dict()
