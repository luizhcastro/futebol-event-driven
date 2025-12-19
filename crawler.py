"""
Crawler - Carrega dados iniciais através de eventos RabbitMQ
Lê arquivos JSON e publica eventos para os microsserviços consumirem
"""

import sys
import json
import logging
from time import sleep

# Adiciona o diretório de messaging ao path
sys.path.insert(0, 'app')

from messaging import (
    RabbitMQConnection,
    EventPublisher,
    Exchanges,
    EventTypes,
    create_jogo_event,
    create_comentario_event,
    create_voto_event
)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Caminhos dos arquivos de dados
JOGOS = "data/jogos.json"
COMENTARIOS = "data/comentarios.json"
VOTACAO = "data/votacao.json"


class EventCrawler:
    """Crawler que publica eventos para popular os serviços"""

    def __init__(self):
        self.connection = None
        self.publisher = None

    def connect(self):
        """Conecta ao RabbitMQ e configura publisher"""
        logger.info("Conectando ao RabbitMQ...")
        self.connection = RabbitMQConnection()
        self.connection.connect()

        self.publisher = EventPublisher(self.connection)

        # Declara exchanges (caso ainda não existam)
        self.publisher.declare_exchange(Exchanges.COMMANDS, 'direct')
        logger.info("Conexão estabelecida e publisher configurado")

    def enviar_jogos(self):
        """Publica eventos de criação de jogos"""
        sucesso = False

        try:
            with open(JOGOS, "r", encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
                jogos = conteudo["jogos"]

            for jogo in jogos:
                event = create_jogo_event(
                    id_jogo=jogo["id_jogo"],
                    time1=jogo["time1"],
                    time2=jogo["time2"],
                    data=jogo["data"]
                )

                self.publisher.publish(
                    exchange=Exchanges.COMMANDS,
                    routing_key=EventTypes.JOGO_CRIAR,
                    message=event
                )

                logger.info(f"Evento publicado: jogo.criar - {jogo['time1']} vs {jogo['time2']}")

            sucesso = True
            logger.info(f"{len(jogos)} jogos publicados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao enviar jogos: {e}")

        return sucesso

    def enviar_comentarios(self):
        """Publica eventos de criação de comentários"""
        sucesso = False

        try:
            with open(COMENTARIOS, "r", encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
                comentarios = conteudo["comentarios"]

            for comentario in comentarios:
                event = create_comentario_event(
                    id_jogo=comentario["id_jogo"],
                    autor=comentario["autor"],
                    comentario=comentario["comentario"]
                )

                self.publisher.publish(
                    exchange=Exchanges.COMMANDS,
                    routing_key=EventTypes.COMENTARIO_CRIAR,
                    message=event
                )

                logger.info(f"Evento publicado: comentario.criar - jogo {comentario['id_jogo']} por {comentario['autor']}")

            sucesso = True
            logger.info(f"{len(comentarios)} comentários publicados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao enviar comentários: {e}")

        return sucesso

    def enviar_votacao(self):
        """Publica eventos de criação de votos"""
        sucesso = False

        try:
            with open(VOTACAO, "r", encoding='utf-8') as arquivo:
                conteudo = json.load(arquivo)
                votacao = conteudo["votacao"]

            for voto in votacao:
                event = create_voto_event(
                    id_jogo=voto["id_jogo"],
                    autor=voto["autor"],
                    voto=voto["voto"]
                )

                self.publisher.publish(
                    exchange=Exchanges.COMMANDS,
                    routing_key=EventTypes.VOTO_CRIAR,
                    message=event
                )

                logger.info(f"Evento publicado: voto.criar - jogo {voto['id_jogo']} por {voto['autor']}: {voto['voto']}")

            sucesso = True
            logger.info(f"{len(votacao)} votos publicados com sucesso")

        except Exception as e:
            logger.error(f"Erro ao enviar votação: {e}")

        return sucesso

    def run(self, loop=True, interval=10):
        """Executa o crawler"""
        logger.info("=" * 60)
        logger.info("Iniciando Event Crawler")
        logger.info("Publicando dados para serviços via RabbitMQ")
        logger.info("=" * 60)

        try:
            self.connect()

            iteration = 1
            while True:
                logger.info(f"\n--- Iteração {iteration} ---")

                if self.enviar_jogos():
                    logger.info("✓ Jogos publicados")
                else:
                    logger.error("✗ Erro publicando jogos")

                # Aguarda um pouco para os jogos serem processados
                sleep(2)

                if self.enviar_comentarios():
                    logger.info("✓ Comentários publicados")
                else:
                    logger.error("✗ Erro publicando comentários")

                if self.enviar_votacao():
                    logger.info("✓ Votação publicada")
                else:
                    logger.error("✗ Erro publicando votação")

                if not loop:
                    logger.info("\nModo único: execução finalizada")
                    break

                logger.info(f"\nAguardando {interval}s para próxima iteração...\n")
                iteration += 1
                sleep(interval)

        except KeyboardInterrupt:
            logger.info("\nCrawler interrompido pelo usuário")
        finally:
            if self.connection:
                self.connection.close()
            logger.info("Crawler encerrado")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Event Crawler - Publica eventos de dados iniciais')
    parser.add_argument('--once', action='store_true', help='Executa apenas uma vez (sem loop)')
    parser.add_argument('--interval', type=int, default=10, help='Intervalo entre iterações em segundos (padrão: 10)')

    args = parser.parse_args()

    crawler = EventCrawler()
    crawler.run(loop=not args.once, interval=args.interval)
