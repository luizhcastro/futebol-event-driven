"""
Serviço de Votação - Arquitetura Event-Driven Simples
API REST para votação + Consumidor de eventos de jogos
"""

from flask import Flask, Response, request
from pymemcache.client import base
from flask_apscheduler import APScheduler
import json
import pika
import os
from time import sleep

VERSAO = "2.0-event-driven-simple"
INFO = {
    "descricao": "Serviço de votação com RabbitMQ (Simples)",
    "autor": "Luiz Henrique",
    "versao": VERSAO,
}

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq")
MEMCACHED_HOST = os.getenv("MEMCACHED_HOST", "banco_votacao")
MEMCACHED_PORT = 11211

servico = Flask("votacao")

# Controle de jogos conhecidos (recebidos via eventos)
jogos_conhecidos = set()


def processar_eventos_jogos():
    """Consome eventos de jogos criados (executado periodicamente)"""
    try:
        credentials = pika.PlainCredentials('admin', 'admin')
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
        )
        channel = connection.channel()
        channel.queue_declare(queue="jogos_eventos", durable=True)

        # Processa mensagens disponíveis
        method_frame, header_frame, body = channel.basic_get(queue="jogos_eventos")

        while method_frame:
            jogo = json.loads(body)
            jogos_conhecidos.add(jogo["id_jogo"])
            print(f"[VOTACAO] Jogo recebido: {jogo['id_jogo']} - {jogo['time1']} vs {jogo['time2']}")

            channel.basic_ack(method_frame.delivery_tag)
            method_frame, header_frame, body = channel.basic_get(queue="jogos_eventos")

        connection.close()

    except Exception as e:
        print(f"[VOTACAO] Erro ao processar eventos: {str(e)}")


@servico.get("/")
def get():
    return Response(json.dumps(INFO), status=200, mimetype="application/json")


@servico.get("/alive")
def is_alive():
    return Response("sim", status=200, mimetype="text/plain")


@servico.post("/votacao/<id_jogo>")
def adicionar_voto(id_jogo):
    """Adiciona voto a um jogo"""
    sucesso = False
    novo_voto = request.get_json()

    try:
        cliente = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))
        votacao_bytes = cliente.get(f"votacao_{id_jogo}")
        votacao = []
        if votacao_bytes:
            votacao = json.loads(votacao_bytes.decode("utf-8"))

        votacao.append(novo_voto)
        cliente.set(f"votacao_{id_jogo}", json.dumps(votacao))
        cliente.close()

        print(f"[VOTACAO] Adicionado ao jogo {id_jogo}: {novo_voto}")
        sucesso = True

    except Exception as e:
        print(f"[VOTACAO] Erro ao adicionar: {str(e)}")

    return Response(status=201 if sucesso else 422)


@servico.get("/votacao/<id_jogo>")
def get_votacao(id_jogo):
    """Busca votação de um jogo"""
    sucesso, votacao = False, []

    try:
        cliente = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))
        votacao_bytes = cliente.get(f"votacao_{id_jogo}")
        if votacao_bytes:
            votacao = json.loads(votacao_bytes.decode("utf-8"))
        cliente.close()
        sucesso = True

    except Exception as e:
        print(f"[VOTACAO] Erro ao buscar: {str(e)}")

    return Response(
        json.dumps(votacao if sucesso else []),
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
    agendador.init_app(servico)
    agendador.add_job(
        id="processar_eventos_jogos",
        func=processar_eventos_jogos,
        trigger="interval",
        seconds=3
    )
    agendador.start()

    # Inicia Flask
    servico.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
