"""
Crawler - Carrega dados iniciais através de HTTP
Lê arquivos JSON e envia via POST para o serviço de jogos
"""

import json
import requests
import os
from time import sleep

JOGOS_SERVICE_URL = os.getenv("JOGOS_SERVICE_URL", "http://localhost:5001")

JOGOS = "data/jogos.json"
COMENTARIOS = "data/comentarios.json"
VOTACAO = "data/votacao.json"


def enviar_jogos():
    """Envia jogos via HTTP POST para o serviço de jogos"""
    sucesso = False

    try:
        with open(JOGOS, "r", encoding="utf-8") as arquivo:
            conteudo = json.load(arquivo)
            jogos = conteudo["jogos"]

        # Envia todos os jogos em uma única requisição POST
        response = requests.post(
            f"{JOGOS_SERVICE_URL}/jogos",
            json=jogos,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code == 201:
            sucesso = True
            print(f"[CRAWLER] {len(jogos)} jogos enviados com sucesso")
            for jogo in jogos:
                print(f"[CRAWLER] Enviado jogo: {jogo['time1']} vs {jogo['time2']}")
        else:
            print(f"[CRAWLER] Erro HTTP {response.status_code} ao enviar jogos")

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
    print("Iniciando Crawler HTTP")
    print(f"Enviando jogos para {JOGOS_SERVICE_URL}")
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
        description="HTTP Crawler - Envia jogos via HTTP POST"
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
