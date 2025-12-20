"""
Serviço de Jogos - Arquitetura Híbrida (HTTP + Eventos)
Recebe jogos via HTTP POST, armazena no Memcached e publica eventos para outros serviços
"""

from flask import Flask, Response, request
from pymemcache.client import base
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
    """Cria conexão simples com RabbitMQ para publicar eventos"""
    credentials = pika.PlainCredentials('admin', 'admin')
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=RABBITMQ_HOST, credentials=credentials)
    )
    channel = connection.channel()
    channel.queue_declare(queue="jogos_eventos", durable=True)
    return channel, connection




@servico.get("/")
def get():
    return Response(json.dumps(INFO), status=200, mimetype="application/json")


@servico.get("/alive")
def is_alive():
    return Response("sim", status=200, mimetype="text/plain")


@servico.post("/jogos")
def criar_jogos():
    """Recebe lista de jogos via HTTP e armazena diretamente no Memcached"""
    sucesso = False
    novos_jogos = request.get_json()

    try:
        cliente = base.Client((MEMCACHED_HOST, MEMCACHED_PORT))

        # Busca jogos existentes
        jogos_bytes = cliente.get("jogos")
        jogos = []
        if jogos_bytes:
            jogos = json.loads(jogos_bytes.decode("utf-8"))

        # Adiciona novos jogos (evitando duplicados)
        for jogo in novos_jogos:
            if not any(j["id_jogo"] == jogo["id_jogo"] for j in jogos):
                jogos.append(jogo)
                print(f"[JOGOS] Armazenado via HTTP: {jogo['time1']} vs {jogo['time2']}", flush=True)
            else:
                print(f"[JOGOS] Jogo duplicado ignorado: {jogo['id_jogo']}", flush=True)

        # Salva de volta no Memcached
        cliente.set("jogos", json.dumps(jogos))
        cliente.close()

        # Publica eventos para outros serviços (Comentarios e Votacao)
        try:
            channel, connection = get_rabbitmq_channel()
            eventos_publicados = 0
            for jogo in novos_jogos:
                # Publica apenas jogos novos (não duplicados)
                if any(j["id_jogo"] == jogo["id_jogo"] for j in jogos):
                    channel.basic_publish(
                        exchange="",
                        routing_key="jogos_eventos",
                        body=json.dumps(jogo),
                        properties=pika.BasicProperties(delivery_mode=2)
                    )
                    eventos_publicados += 1
                    print(f"[JOGOS] Evento publicado para jogos_eventos: {jogo['id_jogo']}", flush=True)
            connection.close()
            print(f"[JOGOS] Total de eventos publicados: {eventos_publicados}", flush=True)
        except Exception as e:
            print(f"[JOGOS] Aviso: Erro ao publicar eventos (não crítico): {str(e)}", flush=True)

        sucesso = True

    except Exception as e:
        print(f"[JOGOS] Erro ao armazenar: {str(e)}")

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

    # Inicia Flask
    servico.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)
