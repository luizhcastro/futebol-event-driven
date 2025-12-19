"""
Cliente Interativo - Arquitetura Event-Driven Simples
Interface CLI para interagir com os microsserviços via REST
"""

import json
import requests
from time import sleep

# URLs dos serviços
JOGOS_URL = "http://localhost:5001"
COMENTARIOS_URL = "http://localhost:5002"
VOTACAO_URL = "http://localhost:5003"


def get_jogos():
    """Busca todos os jogos"""
    try:
        response = requests.get(f"{JOGOS_URL}/jogos")
        if response.status_code == 200:
            return True, response.json()
        return False, []
    except Exception as e:
        print(f"Erro ao buscar jogos: {e}")
        return False, []


def get_comentarios(id_jogo):
    """Busca comentários de um jogo"""
    try:
        response = requests.get(f"{COMENTARIOS_URL}/comentarios/{id_jogo}")
        if response.status_code == 200:
            return True, response.json()
        return False, []
    except Exception as e:
        print(f"Erro ao buscar comentários: {e}")
        return False, []


def get_votacao(id_jogo):
    """Busca votação de um jogo"""
    try:
        response = requests.get(f"{VOTACAO_URL}/votacao/{id_jogo}")
        if response.status_code == 200:
            return True, response.json()
        return False, []
    except Exception as e:
        print(f"Erro ao buscar votação: {e}")
        return False, []


def adicionar_comentario(id_jogo, autor, comentario):
    """Adiciona comentário a um jogo"""
    try:
        payload = {"autor": autor, "comentario": comentario}
        response = requests.post(
            f"{COMENTARIOS_URL}/comentarios/{id_jogo}",
            json=payload
        )
        return response.status_code == 201
    except Exception as e:
        print(f"Erro ao adicionar comentário: {e}")
        return False


def adicionar_voto(id_jogo, autor, voto):
    """Adiciona voto a um jogo"""
    try:
        payload = {"autor": autor, "voto": voto}
        response = requests.post(
            f"{VOTACAO_URL}/votacao/{id_jogo}",
            json=payload
        )
        return response.status_code == 201
    except Exception as e:
        print(f"Erro ao adicionar voto: {e}")
        return False


def imprimir_jogos(jogos):
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              📋 JOGOS DISPONÍVEIS                         ║")
    print("╠════════════════════════════════════════════════════════════╣")
    if jogos:
        for jogo in jogos:
            print(
                f"║  ID: {jogo['id_jogo']:<3} │ {jogo['time1']:<15} x {jogo['time2']:<15} │ {jogo['data']:>10} ║"
            )
    else:
        print("║  Nenhum jogo disponível                                   ║")
    print("╚════════════════════════════════════════════════════════════╝\n")


def imprimir_comentarios(id_jogo, comentarios):
    print(f"\n╔════════════════════════════════════════════════════════════╗")
    print(f"║         💬 COMENTÁRIOS DO JOGO {id_jogo}                         ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    if comentarios:
        for comentario in comentarios:
            print(f"║  👤 {comentario['autor']:<10}: {comentario['comentario']:<42} ║")
    else:
        print("║  Nenhum comentário para este jogo                         ║")
    print("╚════════════════════════════════════════════════════════════╝\n")


def imprimir_votacao(id_jogo, votacao):
    print(f"\n╔════════════════════════════════════════════════════════════╗")
    print(f"║         🗳️  VOTAÇÃO DO JOGO {id_jogo}                            ║")
    print(f"╠════════════════════════════════════════════════════════════╣")
    if votacao:
        for voto in votacao:
            print(f"║  👤 {voto['autor']:<10}: {voto['voto']:<42} ║")
    else:
        print("║  Nenhum voto para este jogo                               ║")
    print("╚════════════════════════════════════════════════════════════╝\n")


def menu_principal():
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║     ⚽ FUTEBOL MICROSERVICES - EVENT-DRIVEN CLI           ║")
    print("╠════════════════════════════════════════════════════════════╣")
    print("║  1. 📋 Listar jogos e detalhes                            ║")
    print("║  2. 💬 Adicionar comentário                               ║")
    print("║  3. 🗳️  Adicionar voto                                     ║")
    print("║  4. 🚪 Sair                                                ║")
    print("╚════════════════════════════════════════════════════════════╝")
    return input("Escolha uma opção: ")


def listar_jogos_e_detalhes():
    """Lista jogos e permite ver detalhes"""
    print("\n🔄 Buscando jogos...")
    sucesso, jogos = get_jogos()

    if not sucesso or not jogos:
        print("❌ Não há jogos disponíveis ou erro ao buscar.")
        return

    imprimir_jogos(jogos)

    id_jogo = input("Digite o ID do jogo para ver detalhes (ou 'v' para voltar): ")
    if id_jogo.lower() == "v":
        return

    try:
        id_jogo = int(id_jogo)

        print(f"\n🔄 Buscando comentários do jogo {id_jogo}...")
        sucesso, comentarios = get_comentarios(id_jogo)
        if sucesso:
            imprimir_comentarios(id_jogo, comentarios)
        else:
            print("❌ Erro ao buscar comentários.")

        print(f"🔄 Buscando votação do jogo {id_jogo}...")
        sucesso, votacao = get_votacao(id_jogo)
        if sucesso:
            imprimir_votacao(id_jogo, votacao)
        else:
            print("❌ Erro ao buscar votação.")

    except ValueError:
        print("❌ ID de jogo inválido.")


def adicionar_novo_comentario():
    """Adiciona um novo comentário"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║         💬 ADICIONAR COMENTÁRIO                           ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        id_jogo = input("Digite o ID do jogo: ")
        autor = input("Digite seu nome: ")
        comentario = input("Digite seu comentário: ")

        print("\n🔄 Adicionando comentário...")
        if adicionar_comentario(id_jogo, autor, comentario):
            print("✅ Comentário adicionado com sucesso!")
        else:
            print("❌ Falha ao adicionar comentário.")

    except Exception as e:
        print(f"❌ Erro: {e}")


def adicionar_novo_voto():
    """Adiciona um novo voto"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║         🗳️  ADICIONAR VOTO                                ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        id_jogo = input("Digite o ID do jogo: ")
        autor = input("Digite seu nome: ")
        voto = input("Digite seu voto (nome do time): ")

        print("\n🔄 Adicionando voto...")
        if adicionar_voto(id_jogo, autor, voto):
            print("✅ Voto adicionado com sucesso!")
        else:
            print("❌ Falha ao adicionar voto.")

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     ⚽ FUTEBOL MICROSERVICES - EVENT-DRIVEN CLI           ║")
    print("║        Arquitetura Event-Driven Simples com RabbitMQ     ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    try:
        while True:
            escolha = menu_principal()

            if escolha == "1":
                listar_jogos_e_detalhes()
            elif escolha == "2":
                adicionar_novo_comentario()
            elif escolha == "3":
                adicionar_novo_voto()
            elif escolha == "4":
                print("\n👋 Saindo... Até logo!\n")
                break
            else:
                print("❌ Opção inválida. Tente novamente.")

            sleep(0.5)

    except KeyboardInterrupt:
        print("\n\n👋 Cliente interrompido pelo usuário. Até logo!\n")
    except Exception as e:
        print(f"\n❌ Erro: {e}\n")
