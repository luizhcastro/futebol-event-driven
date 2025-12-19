"""
Crawler - Carrega dados iniciais através de eventos RabbitMQ (Simples)
Lê arquivos JSON e publica eventos na fila "jogos"
"""

import json
import pika
import os
from time import sleep

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")

JOGOS = "data/jogos.json"
COMENTARIOS = "data/comentarios.json"
VOTACAO = "data/votacao.json"


def get_rabbitmq_channel():
    """Cria conexão simples com RabbitMQ"""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.queue_declare(queue="jogos", durable=True)
    return channel, connection


def enviar_jogos():
    """Publica jogos na fila RabbitMQ"""
    sucesso = False

    try:
        with open(JOGOS, "r", encoding="utf-8") as arquivo:
            conteudo = json.load(arquivo)
            jogos = conteudo["jogos"]

        channel, connection = get_rabbitmq_channel()

        for jogo in jogos:
            mensagem = json.dumps(jogo)
            channel.basic_publish(
                exchange="",
                routing_key="jogos",
                body=mensagem,
                properties=pika.BasicProperties(delivery_mode=2)  # persistent
            )
            print(f"[CRAWLER] Publicado jogo: {jogo['time1']} vs {jogo['time2']}")

        connection.close()
        sucesso = True
        print(f"[CRAWLER] {len(jogos)} jogos publicados com sucesso")

    except Exception as e:
        print(f"[CRAWLER] Erro ao enviar jogos: {e}")

    return sucesso


def enviar_comentarios():
    """Carrega comentários diretamente via REST (não há eventos para comentários iniciais)"""
    print("[CRAWLER] Comentários serão adicionados via client.py ou REST API")
    return True


def enviar_votacao():
    """Carrega votação diretamente via REST (não há eventos para votos iniciais)"""
    print("[CRAWLER] Votos serão adicionados via client.py ou REST API")
    return True


def run_crawler(loop=True, interval=10):
    """Executa o crawler"""
    print("=" * 60)
    print("Iniciando Crawler Simples")
    print("Publicando jogos para RabbitMQ")
    print("=" * 60)

    try:
        iteration = 1
        while True:
            print(f"\n--- Iteração {iteration} ---")

            if enviar_jogos():
                print("✓ Jogos publicados")
            else:
                print("✗ Erro publicando jogos")

            sleep(2)

            enviar_comentarios()
            enviar_votacao()

            if not loop:
                print("\nModo único: execução finalizada")
                break

            print(f"\nAguardando {interval}s para próxima iteração...\n")
            iteration += 1
            sleep(interval)

    except KeyboardInterrupt:
        print("\nCrawler interrompido pelo usuário")
    finally:
        print("Crawler encerrado")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Event Crawler Simples - Publica eventos de jogos"
    )
    parser.add_argument(
        "--once", action="store_true", help="Executa apenas uma vez (sem loop)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=10,
        help="Intervalo entre iterações em segundos (padrão: 10)",
    )

    args = parser.parse_args()

    run_crawler(loop=not args.once, interval=args.interval)
