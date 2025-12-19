"""
Serviço de Comentários - Arquitetura Orientada a Eventos
Gerencia comentários sobre jogos de futebol através de eventos RabbitMQ
"""

import sys
import os
import json
import logging
from pymemcache.client import base

# Adiciona o diretório pai ao path para importar messaging
sys.path.insert(0, '/app')

from messaging import (
    RabbitMQConnection,
    EventPublisher,
    EventConsumer,
    RPCServer,
    Exchanges,
    Queues,
    EventTypes,
    ComentarioEvent,
    JogoEvent
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VERSAO = "2.0-event-driven"
INFO = {
    "descricao": "Serviço que gerencia comentários sobre jogos de futebol (Event-Driven)",
    "autor": "Luiz Henrique",
    "versao": VERSAO,
    "arquitetura": "Event-Driven com RabbitMQ"
}

# Configurações do Memcached
MEMCACHED_HOST = os.getenv('MEMCACHED_HOST', 'banco_comentarios')
MEMCACHED_PORT = 11211


class ComentariosService:
    """Serviço de Comentários com comunicação via eventos"""

    def __init__(self):
        self.memcached_client = None
        self.connection = None
        self.publisher = None
        self.consumer = None
        self.jogos_conhecidos = set()  # Cache de IDs de jogos válidos

    def connect_memcached(self):
        """Conecta ao Memcached"""
        try:
            self.memcached_client = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))
            logger.info(f"Conectado ao Memcached em {MEMCACHED_HOST}:{MEMCACHED_PORT}")
        except Exception as e:
            logger.error(f"Erro ao conectar ao Memcached: {e}")
            raise

    def setup_rabbitmq(self):
        """Configura conexão e estruturas do RabbitMQ"""
        # Conecta ao RabbitMQ
        self.connection = RabbitMQConnection()
        self.connection.connect()

        # Configura publisher
        self.publisher = EventPublisher(self.connection)

        # Declara exchanges (se ainda não existirem)
        self.publisher.declare_exchange(Exchanges.COMMANDS, 'direct')
        self.publisher.declare_exchange(Exchanges.QUERIES, 'direct')
        self.publisher.declare_exchange(Exchanges.EVENTS, 'fanout')

        # Configura consumer
        self.consumer = EventConsumer(self.connection)

        # Declara e vincula fila de comandos
        self.consumer.declare_queue(Queues.COMENTARIOS_COMMAND_CRIAR)
        self.consumer.bind_queue(
            Queues.COMENTARIOS_COMMAND_CRIAR,
            Exchanges.COMMANDS,
            EventTypes.COMENTARIO_CRIAR
        )

        # Declara e vincula fila de queries
        self.consumer.declare_queue(Queues.COMENTARIOS_QUERY_LISTAR)
        self.consumer.bind_queue(
            Queues.COMENTARIOS_QUERY_LISTAR,
            Exchanges.QUERIES,
            EventTypes.QUERY_COMENTARIOS
        )

        # Declara e vincula fila para receber eventos de jogos registrados
        self.consumer.declare_queue(Queues.COMENTARIOS_EVENTS_JOGO)
        self.consumer.bind_queue(
            Queues.COMENTARIOS_EVENTS_JOGO,
            Exchanges.EVENTS,
            EventTypes.JOGO_REGISTRADO
        )

        logger.info("RabbitMQ configurado com sucesso")

    def handle_criar_comentario(self, ch, method, properties, message):
        """Handler para evento comentario.criar"""
        try:
            logger.info(f"Processando evento comentario.criar: {message}")

            # Valida e extrai dados
            comentario_event = ComentarioEvent.from_dict(message)
            id_jogo = comentario_event.id_jogo

            # Obtém comentários existentes para o jogo
            comentarios_existentes = self._get_comentarios_from_memcached(id_jogo)

            # Adiciona novo comentário
            comentarios_existentes.append(comentario_event.to_dict())

            # Salva no Memcached
            self.memcached_client.set(
                f"comentarios_{id_jogo}",
                json.dumps(comentarios_existentes)
            )

            logger.info(f"Comentário adicionado ao jogo {id_jogo} por {comentario_event.autor}")

            # Publica evento comentario.registrado (opcional)
            self.publisher.publish(
                exchange=Exchanges.EVENTS,
                routing_key=EventTypes.COMENTARIO_REGISTRADO,
                message=comentario_event.to_dict()
            )

        except Exception as e:
            logger.error(f"Erro ao processar comentario.criar: {e}")
            raise

    def handle_jogo_registrado(self, ch, method, properties, message):
        """Handler para evento jogo.registrado (para validação)"""
        try:
            jogo_event = JogoEvent.from_dict(message)
            self.jogos_conhecidos.add(jogo_event.id_jogo)
            logger.info(f"Jogo {jogo_event.id_jogo} registrado: {jogo_event.time1} vs {jogo_event.time2}")
        except Exception as e:
            logger.error(f"Erro ao processar jogo.registrado: {e}")

    def handle_query_comentarios(self, message):
        """Handler RPC para query.comentarios"""
        try:
            id_jogo = message.get('id_jogo')
            logger.info(f"Processando query.comentarios para jogo {id_jogo}")

            if id_jogo is None:
                return {
                    "comentarios": [],
                    "total": 0,
                    "status": "error",
                    "error": "id_jogo não fornecido"
                }

            comentarios = self._get_comentarios_from_memcached(id_jogo)

            response = {
                "id_jogo": id_jogo,
                "comentarios": comentarios,
                "total": len(comentarios),
                "status": "success"
            }

            logger.info(f"Query processada: {len(comentarios)} comentários retornados para jogo {id_jogo}")
            return response

        except Exception as e:
            logger.error(f"Erro ao processar query.comentarios: {e}")
            return {
                "comentarios": [],
                "total": 0,
                "status": "error",
                "error": str(e)
            }

    def _get_comentarios_from_memcached(self, id_jogo):
        """Obtém lista de comentários do Memcached para um jogo específico"""
        try:
            comentarios_bytes = self.memcached_client.get(f"comentarios_{id_jogo}")
            if comentarios_bytes:
                return json.loads(comentarios_bytes.decode("utf-8"))
            return []
        except Exception as e:
            logger.error(f"Erro ao ler comentários do Memcached: {e}")
            return []

    def start(self):
        """Inicia o serviço"""
        logger.info("=" * 60)
        logger.info(f"Iniciando {INFO['descricao']}")
        logger.info(f"Versão: {INFO['versao']}")
        logger.info(f"Arquitetura: {INFO['arquitetura']}")
        logger.info("=" * 60)

        # Conecta ao Memcached
        self.connect_memcached()

        # Configura RabbitMQ
        self.setup_rabbitmq()

        # Registra handlers
        self.consumer.subscribe(Queues.COMENTARIOS_COMMAND_CRIAR, self.handle_criar_comentario)
        self.consumer.subscribe(Queues.COMENTARIOS_EVENTS_JOGO, self.handle_jogo_registrado)

        # Configura RPC server
        rpc_server = RPCServer(self.consumer)
        rpc_server.register_rpc_handler(Queues.COMENTARIOS_QUERY_LISTAR, self.handle_query_comentarios)

        # Inicia consumo
        logger.info("Serviço de Comentários pronto para receber eventos!")
        logger.info(f"Consumindo filas:")
        logger.info(f"  - {Queues.COMENTARIOS_COMMAND_CRIAR} (comandos)")
        logger.info(f"  - {Queues.COMENTARIOS_QUERY_LISTAR} (queries RPC)")
        logger.info(f"  - {Queues.COMENTARIOS_EVENTS_JOGO} (eventos de jogos)")
        logger.info("=" * 60)

        try:
            self.consumer.start_consuming()
        except KeyboardInterrupt:
            logger.info("Serviço interrompido pelo usuário")
        finally:
            self.cleanup()

    def cleanup(self):
        """Limpeza de recursos"""
        logger.info("Encerrando serviço...")
        if self.memcached_client:
            self.memcached_client.close()
        if self.connection:
            self.connection.close()
        logger.info("Serviço encerrado")


if __name__ == "__main__":
    service = ComentariosService()
    service.start()
