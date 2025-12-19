"""
Serviço de Votação - Arquitetura Orientada a Eventos
Gerencia votos sobre jogos de futebol através de eventos RabbitMQ
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
    VotoEvent,
    JogoEvent
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

VERSAO = "2.0-event-driven"
INFO = {
    "descricao": "Serviço que gerencia votos sobre jogos de futebol (Event-Driven)",
    "autor": "Luiz Henrique",
    "versao": VERSAO,
    "arquitetura": "Event-Driven com RabbitMQ"
}

# Configurações do Memcached
MEMCACHED_HOST = os.getenv('MEMCACHED_HOST', 'banco_votacao')
MEMCACHED_PORT = 11211


class VotacaoService:
    """Serviço de Votação com comunicação via eventos"""

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
        self.consumer.declare_queue(Queues.VOTACAO_COMMAND_CRIAR)
        self.consumer.bind_queue(
            Queues.VOTACAO_COMMAND_CRIAR,
            Exchanges.COMMANDS,
            EventTypes.VOTO_CRIAR
        )

        # Declara e vincula fila de queries
        self.consumer.declare_queue(Queues.VOTACAO_QUERY_LISTAR)
        self.consumer.bind_queue(
            Queues.VOTACAO_QUERY_LISTAR,
            Exchanges.QUERIES,
            EventTypes.QUERY_VOTACAO
        )

        # Declara e vincula fila para receber eventos de jogos registrados
        self.consumer.declare_queue(Queues.VOTACAO_EVENTS_JOGO)
        self.consumer.bind_queue(
            Queues.VOTACAO_EVENTS_JOGO,
            Exchanges.EVENTS,
            EventTypes.JOGO_REGISTRADO
        )

        logger.info("RabbitMQ configurado com sucesso")

    def handle_criar_voto(self, ch, method, properties, message):
        """Handler para evento voto.criar"""
        try:
            logger.info(f"Processando evento voto.criar: {message}")

            # Valida e extrai dados
            voto_event = VotoEvent.from_dict(message)
            id_jogo = voto_event.id_jogo

            # Obtém votos existentes para o jogo
            votos_existentes = self._get_votacao_from_memcached(id_jogo)

            # Adiciona novo voto
            votos_existentes.append(voto_event.to_dict())

            # Salva no Memcached
            self.memcached_client.set(
                f"votacao_{id_jogo}",
                json.dumps(votos_existentes)
            )

            logger.info(f"Voto adicionado ao jogo {id_jogo} por {voto_event.autor}: {voto_event.voto}")

            # Publica evento voto.registrado (opcional)
            self.publisher.publish(
                exchange=Exchanges.EVENTS,
                routing_key=EventTypes.VOTO_REGISTRADO,
                message=voto_event.to_dict()
            )

        except Exception as e:
            logger.error(f"Erro ao processar voto.criar: {e}")
            raise

    def handle_jogo_registrado(self, ch, method, properties, message):
        """Handler para evento jogo.registrado (para validação)"""
        try:
            jogo_event = JogoEvent.from_dict(message)
            self.jogos_conhecidos.add(jogo_event.id_jogo)
            logger.info(f"Jogo {jogo_event.id_jogo} registrado: {jogo_event.time1} vs {jogo_event.time2}")
        except Exception as e:
            logger.error(f"Erro ao processar jogo.registrado: {e}")

    def handle_query_votacao(self, message):
        """Handler RPC para query.votacao"""
        try:
            id_jogo = message.get('id_jogo')
            logger.info(f"Processando query.votacao para jogo {id_jogo}")

            if id_jogo is None:
                return {
                    "votacao": [],
                    "total": 0,
                    "status": "error",
                    "error": "id_jogo não fornecido"
                }

            votacao = self._get_votacao_from_memcached(id_jogo)

            response = {
                "id_jogo": id_jogo,
                "votacao": votacao,
                "total": len(votacao),
                "status": "success"
            }

            logger.info(f"Query processada: {len(votacao)} votos retornados para jogo {id_jogo}")
            return response

        except Exception as e:
            logger.error(f"Erro ao processar query.votacao: {e}")
            return {
                "votacao": [],
                "total": 0,
                "status": "error",
                "error": str(e)
            }

    def _get_votacao_from_memcached(self, id_jogo):
        """Obtém lista de votos do Memcached para um jogo específico"""
        try:
            votacao_bytes = self.memcached_client.get(f"votacao_{id_jogo}")
            if votacao_bytes:
                return json.loads(votacao_bytes.decode("utf-8"))
            return []
        except Exception as e:
            logger.error(f"Erro ao ler votação do Memcached: {e}")
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
        self.consumer.subscribe(Queues.VOTACAO_COMMAND_CRIAR, self.handle_criar_voto)
        self.consumer.subscribe(Queues.VOTACAO_EVENTS_JOGO, self.handle_jogo_registrado)

        # Configura RPC server
        rpc_server = RPCServer(self.consumer)
        rpc_server.register_rpc_handler(Queues.VOTACAO_QUERY_LISTAR, self.handle_query_votacao)

        # Inicia consumo
        logger.info("Serviço de Votação pronto para receber eventos!")
        logger.info(f"Consumindo filas:")
        logger.info(f"  - {Queues.VOTACAO_COMMAND_CRIAR} (comandos)")
        logger.info(f"  - {Queues.VOTACAO_QUERY_LISTAR} (queries RPC)")
        logger.info(f"  - {Queues.VOTACAO_EVENTS_JOGO} (eventos de jogos)")
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
    service = VotacaoService()
    service.start()
