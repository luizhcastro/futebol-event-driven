"""
Serviço de Jogos - Arquitetura Event-Driven Simples
Recebe requisições REST, publica eventos no RabbitMQ e consome eventos de jogos
"""

from flask import Flask, Response, request
from pymemcache.client import base
from flask_apscheduler import APScheduler
import json
import pika
import os

VERSAO = "2.0-event-driven-simple"
INFO = {
    "descricao": "Serviço de jogos com RabbitMQ (Simples)",
    "autor": "Luiz Henrique",
    "versao": VERSAO,
}

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "banco_jogos")
MEMCACHED_PORT = 11211

servico = Flask("jogos")


def get_rabbitmq_channel():
    """Cria conexão simples com RabbitMQ"""
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST)
    )
    channel = connection.channel()
    channel.queue_declare(queue="jogos", durable=True)
    channel.queue_declare(queue="jogos_eventos", durable=True)
    return channel, connection


def processar_eventos_jogos():
    """Consome eventos de jogos criados e armazena no Memcached"""
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST)
        )
        channel = connection.channel()
        channel.queue_declare(queue="jogos", durable=True)
        channel.queue_declare(queue="jogos_eventos", durable=True)

        # Processa mensagens disponíveis
        method_frame, header_frame, body = channel.basic_get(queue="jogos")

        while method_frame:
            jogo = json.loads(body)

            # Armazena no Memcached
            try:
                cliente = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))
                jogos_bytes = cliente.get("jogos")
                jogos = []
                if jogos_bytes:
                    jogos = json.loads(jogos_bytes.decode("utf-8"))

                # Evita duplicados
                if not any(j["id_jogo"] == jogo["id_jogo"] for j in jogos):
                    jogos.append(jogo)
                    cliente.set("jogos", json.dumps(jogos))
                    print(f"[JOGOS] Armazenado: {jogo['time1']} vs {jogo['time2']}")

                    # Publica para jogos_eventos (para Comentarios e Votacao)
                    channel.basic_publish(
                        exchange="",
                        routing_key="jogos_eventos",
                        body=json.dumps(jogo),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )
                    print(f"[JOGOS] Evento publicado para jogos_eventos")

                cliente.close()
            except Exception as e:
                print(f"[JOGOS] Erro ao armazenar: {str(e)}")

            channel.basic_ack(method_frame.delivery_tag)
            method_frame, header_frame, body = channel.basic_get(queue="jogos")

        connection.close()

    except Exception as e:
        print(f"[JOGOS] Erro ao processar eventos: {str(e)}")


@servico.get("/")
def get():
    return Response(json.dumps(INFO), status=200, mimetype="application/json")


@servico.get("/alive")
def is_alive():
    return Response("sim", status=200, mimetype="text/plain")


@servico.post("/jogos")
def criar_jogos():
    """Recebe lista de jogos e publica no RabbitMQ"""
    sucesso = False
    novos_jogos = request.get_json()

    try:
        # Publica cada jogo no RabbitMQ
        channel, connection = get_rabbitmq_channel()

        for jogo in novos_jogos:
            mensagem = json.dumps(jogo)
            channel.basic_publish(
                exchange="",
                routing_key="jogos",
                body=mensagem,
                properties=pika.BasicProperties(delivery_mode=2)  # persistent
            )
            print(f"[JOGOS] Publicado: {jogo}")

        connection.close()
        sucesso = True

    except Exception as e:
        print(f"[JOGOS] Erro ao publicar: {str(e)}")

    return Response(status=201 if sucesso else 422)


@servico.get("/jogos")
def get_jogos():
    """Consulta jogos do Memcached"""
    sucesso, jogos = False, None

    try:
        cliente = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))
        jogos_bytes = cliente.get("jogos")
        if jogos_bytes:
            jogos = json.loads(jogos_bytes.decode("utf-8"))
        cliente.close()
        sucesso = True

    except Exception as e:
        print(f"[JOGOS] Erro ao buscar: {str(e)}")

    return Response(
        json.dumps(jogos if sucesso and jogos else []),
        status=200 if sucesso else 500,
        mimetype="application/json",
    )


if __name__ == "__main__":
    print("=" * 60)
    print(f"Iniciando {INFO['descricao']}")
    print(f"Versão: {INFO['versao']}")
    print("=" * 60)

    # Inicia agendador para processar eventos em background
    agendador = APScheduler()
    agendador.add_job(
        id="processar_eventos_jogos",
        func=processar_eventos_jogos,
        trigger="interval",
        seconds=3
    )
    agendador.start()

    # Inicia Flask
    servico.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
