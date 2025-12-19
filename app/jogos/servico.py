"""
Serviço de Jogos - Arquitetura Orientada a Eventos
Gerencia informações de jogos de futebol através de eventos RabbitMQ
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
    JogoEvent
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VERSAO = "2.0-event-driven"
INFO = {
    "descricao": "Serviço que gerencia informações sobre jogos de futebol (Event-Driven)",
    "autor": "Luiz Henrique",
    "versao": VERSAO,
    "arquitetura": "Event-Driven com RabbitMQ"
}

# Configurações do Memcached
MEMCACHED_HOST = os.getenv('MEMCACHED_HOST', 'banco_jogos')
MEMCACHED_PORT = 11211


class JogosService:
    """Serviço de Jogos com comunicação via eventos"""

    def __init__(self):
        self.memcached_client = None
        self.connection = None
        self.publisher = None
        self.consumer = None

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

        # Declara exchanges
        self.publisher.declare_exchange(Exchanges.COMMANDS, 'direct')
        self.publisher.declare_exchange(Exchanges.QUERIES, 'direct')
        self.publisher.declare_exchange(Exchanges.EVENTS, 'fanout')

        # Configura consumer
        self.consumer = EventConsumer(self.connection)

        # Declara e vincula fila de comandos
        self.consumer.declare_queue(Queues.JOGOS_COMMAND_CRIAR)
        self.consumer.bind_queue(
            Queues.JOGOS_COMMAND_CRIAR,
            Exchanges.COMMANDS,
            EventTypes.JOGO_CRIAR
        )

        # Declara e vincula fila de queries
        self.consumer.declare_queue(Queues.JOGOS_QUERY_LISTAR)
        self.consumer.bind_queue(
            Queues.JOGOS_QUERY_LISTAR,
            Exchanges.QUERIES,
            EventTypes.QUERY_JOGOS
        )

        logger.info("RabbitMQ configurado com sucesso")

    def handle_criar_jogo(self, ch, method, properties, message):
        """Handler para evento jogo.criar"""
        try:
            logger.info(f"Processando evento jogo.criar: {message}")

            # Valida e extrai dados
            jogo_event = JogoEvent.from_dict(message)

            # Obtém jogos existentes
            jogos_existentes = self._get_jogos_from_memcached()

            # Atualiza ou adiciona jogo
            found = False
            for i, jogo_existente in enumerate(jogos_existentes):
                if jogo_existente["id_jogo"] == jogo_event.id_jogo:
                    jogos_existentes[i] = jogo_event.to_dict()
                    found = True
                    logger.info(f"Jogo {jogo_event.id_jogo} atualizado")
                    break

            if not found:
                jogos_existentes.append(jogo_event.to_dict())
                logger.info(f"Jogo {jogo_event.id_jogo} criado")

            # Salva no Memcached
            self.memcached_client.set("jogos", json.dumps(jogos_existentes))

            # Publica evento jogo.registrado para outros serviços
            self.publisher.publish(
                exchange=Exchanges.EVENTS,
                routing_key=EventTypes.JOGO_REGISTRADO,
                message=jogo_event.to_dict()
            )

            logger.info(f"Jogo {jogo_event.id_jogo} processado e evento publicado")

        except Exception as e:
            logger.error(f"Erro ao processar jogo.criar: {e}")
            raise

    def handle_query_jogos(self, message):
        """Handler RPC para query.jogos"""
        try:
            logger.info("Processando query.jogos")

            jogos = self._get_jogos_from_memcached()

            response = {
                "jogos": jogos,
                "total": len(jogos),
                "status": "success"
            }

            logger.info(f"Query processada: {len(jogos)} jogos retornados")
            return response

        except Exception as e:
            logger.error(f"Erro ao processar query.jogos: {e}")
            return {
                "jogos": [],
                "total": 0,
                "status": "error",
                "error": str(e)
            }

    def _get_jogos_from_memcached(self):
        """Obtém lista de jogos do Memcached"""
        try:
            jogos_bytes = self.memcached_client.get("jogos")
            if jogos_bytes:
                return json.loads(jogos_bytes.decode("utf-8"))
            return []
        except Exception as e:
            logger.error(f"Erro ao ler jogos do Memcached: {e}")
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
        self.consumer.subscribe(Queues.JOGOS_COMMAND_CRIAR, self.handle_criar_jogo)

        # Configura RPC server
        rpc_server = RPCServer(self.consumer)
        rpc_server.register_rpc_handler(Queues.JOGOS_QUERY_LISTAR, self.handle_query_jogos)

        # Inicia consumo
        logger.info("Serviço de Jogos pronto para receber eventos!")
        logger.info(f"Consumindo filas:")
        logger.info(f"  - {Queues.JOGOS_COMMAND_CRIAR} (comandos)")
        logger.info(f"  - {Queues.JOGOS_QUERY_LISTAR} (queries RPC)")
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
    service = JogosService()
    service.start()
