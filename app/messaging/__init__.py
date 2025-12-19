"""
Módulo de mensageria compartilhado para comunicação via RabbitMQ
"""

from .rabbitmq_client import (
    RabbitMQConnection,
    EventPublisher,
    EventConsumer,
    RPCClient,
    RPCServer
)

from .events import (
    JogoEvent,
    ComentarioEvent,
    VotoEvent,
    QueryEvent,
    EventTypes,
    Exchanges,
    Queues,
    create_jogo_event,
    create_comentario_event,
    create_voto_event,
    create_query_event
)

__all__ = [
    # Classes de conexão
    'RabbitMQConnection',
    'EventPublisher',
    'EventConsumer',
    'RPCClient',
    'RPCServer',

    # Eventos
    'JogoEvent',
    'ComentarioEvent',
    'VotoEvent',
    'QueryEvent',

    # Constantes
    'EventTypes',
    'Exchanges',
    'Queues',

    # Helpers
    'create_jogo_event',
    'create_comentario_event',
    'create_voto_event',
    'create_query_event',
]
