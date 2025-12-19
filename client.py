"""
Cliente Interativo - Arquitetura Orientada a Eventos
Interface CLI para interagir com os microsserviços via RabbitMQ
Usa padrão RPC para queries e fire-and-forget para comandos
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
    RPCClient,
    Exchanges,
    EventTypes,
    create_comentario_event,
    create_voto_event
)

logging.basicConfig(level=logging.WARNING)  # Menos verboso para CLI
logger = logging.getLogger(__name__)


class FutebolRPCClient:
    """Cliente RPC para interagir com os microsserviços"""

    def __init__(self):
        self.connection = None
        self.rpc_client = None
        self.publisher = None

    def connect(self):
        """Conecta ao RabbitMQ"""
        print("Conectando aos serviços...")
        self.connection = RabbitMQConnection()
        self.connection.connect()

        # RPC client para queries
        self.rpc_client = RPCClient(self.connection)

        # Publisher para comandos
        self.publisher = EventPublisher(self.connection)
        self.publisher.declare_exchange(Exchanges.COMMANDS, 'direct')
        self.publisher.declare_exchange(Exchanges.QUERIES, 'direct')

        print("Conectado com sucesso!\n")

    def get_jogos(self):
        """Busca todos os jogos via RPC"""
        try:
            response = self.rpc_client.call(
                exchange=Exchanges.QUERIES,
                routing_key=EventTypes.QUERY_JOGOS,
                message={"request_id": "get_jogos"},
                timeout=5
            )

            if response and response.get('status') == 'success':
                return True, response.get('jogos', [])
            else:
                return False, []

        except Exception as e:
            logger.error(f"Erro ao buscar jogos: {e}")
            return False, []

    def get_comentarios(self, id_jogo):
        """Busca comentários de um jogo via RPC"""
        try:
            response = self.rpc_client.call(
                exchange=Exchanges.QUERIES,
                routing_key=EventTypes.QUERY_COMENTARIOS,
                message={"request_id": "get_comentarios", "id_jogo": int(id_jogo)},
                timeout=5
            )

            if response and response.get('status') == 'success':
                return True, response.get('comentarios', [])
            else:
                return False, []

        except Exception as e:
            logger.error(f"Erro ao buscar comentários: {e}")
            return False, []

    def get_votacao(self, id_jogo):
        """Busca votos de um jogo via RPC"""
        try:
            response = self.rpc_client.call(
                exchange=Exchanges.QUERIES,
                routing_key=EventTypes.QUERY_VOTACAO,
                message={"request_id": "get_votacao", "id_jogo": int(id_jogo)},
                timeout=5
            )

            if response and response.get('status') == 'success':
                return True, response.get('votacao', [])
            else:
                return False, []

        except Exception as e:
            logger.error(f"Erro ao buscar votação: {e}")
            return False, []

    def adicionar_comentario(self, id_jogo, autor, comentario):
        """Adiciona comentário via evento (fire-and-forget)"""
        try:
            event = create_comentario_event(
                id_jogo=int(id_jogo),
                autor=autor,
                comentario=comentario
            )

            self.publisher.publish(
                exchange=Exchanges.COMMANDS,
                routing_key=EventTypes.COMENTARIO_CRIAR,
                message=event
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar comentário: {e}")
            return False

    def adicionar_voto(self, id_jogo, autor, voto):
        """Adiciona voto via evento (fire-and-forget)"""
        try:
            event = create_voto_event(
                id_jogo=int(id_jogo),
                autor=autor,
                voto=voto
            )

            self.publisher.publish(
                exchange=Exchanges.COMMANDS,
                routing_key=EventTypes.VOTO_CRIAR,
                message=event
            )

            return True

        except Exception as e:
            logger.error(f"Erro ao adicionar voto: {e}")
            return False

    def close(self):
        """Fecha a conexão"""
        if self.connection:
            self.connection.close()


# Funções de impressão
def imprimir_jogos(jogos):
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║              📋 JOGOS DISPONÍVEIS                         ║")
    print("╠════════════════════════════════════════════════════════════╣")
    if jogos:
        for jogo in jogos:
            print(f"║  ID: {jogo['id_jogo']:<3} │ {jogo['time1']:<15} x {jogo['time2']:<15} │ {jogo['data']:>10} ║")
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


def listar_jogos_e_detalhes(client):
    """Lista jogos e permite ver detalhes"""
    print("\n🔄 Buscando jogos...")
    sucesso, jogos = client.get_jogos()

    if not sucesso or not jogos:
        print("❌ Não há jogos disponíveis ou erro ao buscar.")
        return

    imprimir_jogos(jogos)

    id_jogo = input("Digite o ID do jogo para ver detalhes (ou 'v' para voltar): ")
    if id_jogo.lower() == 'v':
        return

    try:
        id_jogo = int(id_jogo)

        # Busca comentários
        print(f"\n🔄 Buscando comentários do jogo {id_jogo}...")
        sucesso, comentarios = client.get_comentarios(id_jogo)
        if sucesso:
            imprimir_comentarios(id_jogo, comentarios)
        else:
            print("❌ Erro ao buscar comentários.")

        # Busca votação
        print(f"🔄 Buscando votação do jogo {id_jogo}...")
        sucesso, votacao = client.get_votacao(id_jogo)
        if sucesso:
            imprimir_votacao(id_jogo, votacao)
        else:
            print("❌ Erro ao buscar votação.")

    except ValueError:
        print("❌ ID de jogo inválido.")


def adicionar_novo_comentario(client):
    """Adiciona um novo comentário"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║         💬 ADICIONAR COMENTÁRIO                           ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        id_jogo = input("Digite o ID do jogo: ")
        autor = input("Digite seu nome: ")
        comentario = input("Digite seu comentário: ")

        print("\n🔄 Publicando evento de comentário...")
        if client.adicionar_comentario(id_jogo, autor, comentario):
            print("✅ Evento de comentário publicado com sucesso!")
            print("   (O comentário será processado assincronamente)")
        else:
            print("❌ Falha ao publicar evento de comentário.")

    except Exception as e:
        print(f"❌ Erro: {e}")


def adicionar_novo_voto(client):
    """Adiciona um novo voto"""
    print("\n╔════════════════════════════════════════════════════════════╗")
    print("║         🗳️  ADICIONAR VOTO                                ║")
    print("╚════════════════════════════════════════════════════════════╝")

    try:
        id_jogo = input("Digite o ID do jogo: ")
        autor = input("Digite seu nome: ")
        voto = input("Digite seu voto (nome do time): ")

        print("\n🔄 Publicando evento de voto...")
        if client.adicionar_voto(id_jogo, autor, voto):
            print("✅ Evento de voto publicado com sucesso!")
            print("   (O voto será processado assincronamente)")
        else:
            print("❌ Falha ao publicar evento de voto.")

    except Exception as e:
        print(f"❌ Erro: {e}")


if __name__ == "__main__":
    print("╔════════════════════════════════════════════════════════════╗")
    print("║     ⚽ FUTEBOL MICROSERVICES - EVENT-DRIVEN CLI           ║")
    print("║        Arquitetura Orientada a Eventos com RabbitMQ       ║")
    print("╚════════════════════════════════════════════════════════════╝\n")

    client = FutebolRPCClient()

    try:
        client.connect()

        while True:
            escolha = menu_principal()

            if escolha == "1":
                listar_jogos_e_detalhes(client)
            elif escolha == "2":
                adicionar_novo_comentario(client)
            elif escolha == "3":
                adicionar_novo_voto(client)
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
    finally:
        client.close()
