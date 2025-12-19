# Microsserviços de Futebol - Arquitetura Orientada a Eventos (Simples)

Sistema de gerenciamento de jogos de futebol, comentários e votos usando **arquitetura event-driven** com **RabbitMQ**.

## 🎥 Vídeo Explicativo
[Assistir vídeo no YouTube](https://youtu.be/RFR7ClFlA1M)

---

## 🏗️ Arquitetura Event-Driven Simplificada

### O que é Arquitetura Orientada a Eventos?

Ao invés dos microsserviços se comunicarem **diretamente via HTTP**, eles se comunicam **através de mensagens** usando um **message broker** (RabbitMQ).

**Vantagens:**
- 🔌 **Desacoplamento:** Serviços não conhecem uns aos outros diretamente
- 🛡️ **Resiliência:** Mensagens não se perdem se um serviço cair temporariamente
- 📈 **Escalabilidade:** Fácil adicionar múltiplos consumidores para a mesma fila
- ⚡ **Assíncrono:** Processamento não-bloqueante

### Como Funciona?

```
┌─────────────┐
│   Crawler   │ ──┐
└─────────────┘   │
                  │ publica eventos
                  ↓
         ┌────────────────┐
         │ Fila "jogos"   │
         └────────┬───────┘
                  │ consome (APScheduler a cada 3s)
                  ↓
         ┌──────────────────────┐
         │   Serviço Jogos      │
         │  - Armazena no DB    │
         │  - Publica evento    │
         └──────────┬───────────┘
                    │ publica
                    ↓
         ┌──────────────────────┐
         │ Fila "jogos_eventos" │
         └──────┬──────────┬────┘
                │          │ consome (APScheduler a cada 3s)
          ┌─────┘          └─────┐
          ↓                      ↓
┌──────────────────┐   ┌──────────────────┐
│ Serviço          │   │ Serviço          │
│ Comentários      │   │ Votação          │
│ - REST API       │   │ - REST API       │
└────────┬─────────┘   └─────────┬────────┘
         │                       │
         └───────────┬───────────┘
                     │ HTTP GET/POST
                     ↓
              ┌─────────────┐
              │   Client    │
              └─────────────┘
```

---

## 📬 Sistema de Filas

### Filas RabbitMQ

| Fila | Produtor | Consumidor | Função |
|------|----------|------------|--------|
| `jogos` | Crawler | Serviço Jogos | Distribuir eventos de criação de jogos |
| `jogos_eventos` | Serviço Jogos | Comentários + Votação | Notificar quando jogo é registrado |

### Fluxo Completo

1. **Crawler** lê `data/jogos.json` e publica eventos na fila `jogos`
2. **Serviço Jogos** consome da fila `jogos` (polling a cada 3s)
   - Armazena jogo no Memcached
   - Publica evento na fila `jogos_eventos`
3. **Serviços Comentários e Votação** consomem da fila `jogos_eventos` (polling a cada 3s)
   - Atualizam cache local de jogos conhecidos
4. **Client** faz requisições REST para adicionar comentários/votos
   - `POST http://localhost:5002/comentarios/{id_jogo}`
   - `POST http://localhost:5003/votacao/{id_jogo}`

---

## 🔧 Componentes

### 1. Serviço de Jogos (porta 5001)
- **REST API**: `GET /jogos`, `POST /jogos`
- **Consumer**: Consome fila `jogos` e armazena no Memcached
- **Producer**: Publica na fila `jogos_eventos`
- **Polling**: APScheduler executa a cada 3 segundos

### 2. Serviço de Comentários (porta 5002)
- **REST API**: `GET /comentarios/{id_jogo}`, `POST /comentarios/{id_jogo}`
- **Consumer**: Consome fila `jogos_eventos` para saber quais jogos existem
- **Storage**: Memcached (chave: `comentarios_{id_jogo}`)
- **Polling**: APScheduler executa a cada 3 segundos

### 3. Serviço de Votação (porta 5003)
- **REST API**: `GET /votacao/{id_jogo}`, `POST /votacao/{id_jogo}`
- **Consumer**: Consome fila `jogos_eventos` para saber quais jogos existem
- **Storage**: Memcached (chave: `votacao_{id_jogo}`)
- **Polling**: APScheduler executa a cada 3 segundos

### 4. Crawler
- **Função**: Carrega dados iniciais de `data/jogos.json`
- **Producer**: Publica eventos na fila `jogos`
- **Execução**: `python3 crawler.py --once` (executa uma vez)

### 5. Client
- **Interface**: CLI interativo
- **Comunicação**: REST API com biblioteca `requests`
- **Funções**:
  - Listar jogos
  - Ver comentários e votação
  - Adicionar comentários e votos

---

## 🚀 Como Executar

### Pré-requisitos
- Docker e Docker Compose instalados
- Python 3.9+ (para executar client e crawler fora do Docker)

### Passo 1: Subir os Serviços

```bash
# No diretório raiz do projeto
docker-compose up --build
```

Isso iniciará:
- **RabbitMQ** (porta 5672 para AMQP, porta 15672 para UI)
- **Serviço Jogos** (porta 5001)
- **Serviço Comentários** (porta 5002)
- **Serviço Votação** (porta 5003)
- **3 instâncias Memcached** (portas 11211, 11212, 11213)

### Passo 2: Acessar o RabbitMQ Management

Abra o navegador em: `http://localhost:15672`
- **Usuário**: `admin`
- **Senha**: `admin`

Você pode visualizar:
- Filas criadas (`jogos`, `jogos_eventos`)
- Mensagens sendo publicadas e consumidas
- Conexões ativas dos serviços

### Passo 3: Carregar Dados Iniciais

Em outro terminal, execute o crawler para popular os jogos:

```bash
# Instalar dependências (se necessário)
pip3 install -r requirements.txt

# Executar crawler (modo único - executa uma vez)
python3 crawler.py --once
```

Você verá logs como:
```
[CRAWLER] Publicado jogo: Flamengo vs Vasco
[CRAWLER] Publicado jogo: Corinthians vs Palmeiras
✓ Jogos publicados
```

### Passo 4: Executar o Client Interativo

```bash
python3 client.py
```

Menu interativo:
```
╔════════════════════════════════════════════════════════════╗
║     ⚽ FUTEBOL MICROSERVICES - EVENT-DRIVEN CLI           ║
╠════════════════════════════════════════════════════════════╣
║  1. 📋 Listar jogos e detalhes                            ║
║  2. 💬 Adicionar comentário                               ║
║  3. 🗳️  Adicionar voto                                     ║
║  4. 🚪 Sair                                                ║
╚════════════════════════════════════════════════════════════╝
```

---

## 📊 Padrões de Mensageria

### 1. Work Queue (Fila de Trabalho)
- **Fila**: `jogos`
- **Padrão**: Um produtor (Crawler) → Uma fila → Um consumidor (Serviço Jogos)
- **Uso**: Distribuir trabalho de criação de jogos
- **Características**:
  - Mensagens persistentes (`delivery_mode=2`)
  - Acknowledgment manual (`basic_ack`)
  - Processamento assíncrono com polling

### 2. Fan-out Simplificado
- **Fila**: `jogos_eventos`
- **Padrão**: Um produtor (Serviço Jogos) → Uma fila → Múltiplos consumidores (Comentários + Votação)
- **Uso**: Notificar múltiplos serviços sobre novo jogo
- **Implementação**: Cada serviço consome da mesma fila usando `basic_get()`

---

## 🛠️ Stack Técnica

| Componente | Tecnologia | Versão |
|------------|------------|--------|
| Message Broker | RabbitMQ | 3-management |
| Serviços | Flask | Latest |
| Cliente RabbitMQ | Pika | ≥1.3.0 |
| Polling | APScheduler (Flask-APScheduler) | Latest |
| Cache/DB | Memcached | Latest |
| Cliente HTTP | Requests | Latest |
| Orquestração | Docker Compose | Latest |

---

## 📁 Estrutura do Projeto

```
futebol-event-driven/
├── app/
│   ├── jogos/
│   │   └── servico.py          # Serviço Jogos (Flask + Consumer + Producer)
│   ├── comentarios/
│   │   └── servico.py          # Serviço Comentários (Flask + Consumer)
│   └── votacao/
│       └── servico.py          # Serviço Votação (Flask + Consumer)
├── data/
│   ├── jogos.json              # Dados de jogos
│   ├── comentarios.json        # Dados de comentários (não usado)
│   └── votacao.json            # Dados de votação (não usado)
├── crawler.py                  # Crawler para carregar dados
├── client.py                   # Cliente CLI interativo
├── docker-compose.yml          # Orquestração de containers
├── Dockerfile                  # Imagem base dos serviços
├── requirements.txt            # Dependências Python
├── README.md                   # Este arquivo
└── SIMPLIFICACAO.md            # Documentação da simplificação
```

---

## 🔍 Detalhes de Implementação

### APScheduler (Polling)

Cada serviço usa APScheduler para executar polling periodicamente:

```python
from flask_apscheduler import APScheduler

def processar_eventos():
    # Conecta ao RabbitMQ
    # Faz basic_get() da fila
    # Processa mensagens
    # Faz basic_ack() para confirmar
    pass

# No main:
agendador = APScheduler()
agendador.add_job(
    id="processar_eventos",
    func=processar_eventos,
    trigger="interval",
    seconds=3  # Executa a cada 3 segundos
)
agendador.start()
```

### Pika (Cliente RabbitMQ)

Comunicação simples com RabbitMQ sem abstrações:

```python
import pika

# Publicar mensagem
connection = pika.BlockingConnection(
    pika.ConnectionParameters(host='rabbitmq')
)
channel = connection.channel()
channel.queue_declare(queue='jogos', durable=True)
channel.basic_publish(
    exchange='',
    routing_key='jogos',
    body=json.dumps(mensagem),
    properties=pika.BasicProperties(delivery_mode=2)  # persistente
)
connection.close()

# Consumir mensagem
method_frame, header_frame, body = channel.basic_get(queue='jogos')
if method_frame:
    mensagem = json.loads(body)
    # Processar mensagem...
    channel.basic_ack(method_frame.delivery_tag)
```

---

## 🧪 Testando o Sistema

### 1. Verificar se RabbitMQ está rodando
```bash
docker ps | grep rabbitmq
```

### 2. Ver logs dos serviços
```bash
docker-compose logs -f jogos
docker-compose logs -f comentarios
docker-compose logs -f votacao
```

### 3. Acessar Management UI
- URL: http://localhost:15672
- Login: admin / admin
- Verificar filas: `jogos`, `jogos_eventos`
- Ver mensagens sendo processadas

### 4. Testar REST API diretamente
```bash
# Listar jogos
curl http://localhost:5001/jogos

# Adicionar comentário
curl -X POST http://localhost:5002/comentarios/1 \
  -H "Content-Type: application/json" \
  -d '{"autor": "João", "comentario": "Que jogo!"}'

# Ver comentários
curl http://localhost:5002/comentarios/1
```

---

## 🎓 Conceitos Aprendidos

Este projeto demonstra na prática:

1. **Arquitetura Orientada a Eventos (Event-Driven Architecture)**
   - Comunicação via mensagens ao invés de chamadas diretas
   - Desacoplamento entre serviços

2. **Message Broker (RabbitMQ)**
   - Filas persistentes (durable queues)
   - Acknowledgment manual
   - Produtores e consumidores

3. **Padrões de Mensageria**
   - Work Queue (distribuição de trabalho)
   - Fan-out simplificado (notificação para múltiplos serviços)

4. **Microsserviços**
   - Serviços independentes
   - Cada serviço com seu próprio banco de dados (Memcached)
   - APIs REST para comunicação externa

5. **Polling com APScheduler**
   - Execução periódica de tarefas
   - Processamento assíncrono

---

## 🆚 Comparação com Kafka

Este projeto é intencionalmente simples, similar a projetos básicos com Kafka:

| Aspecto | RabbitMQ (este projeto) | Kafka |
|---------|-------------------------|-------|
| Biblioteca Python | `pika` | `confluent-kafka` |
| Consumer | `basic_get()` com polling | `consumer.poll()` |
| Producer | `basic_publish()` | `producer.produce()` |
| Polling | APScheduler (3s) | Loop próprio do Kafka |
| Complexidade | Simples | Simples |
| Abstrações | Mínimas (chamadas diretas) | Mínimas |

---

## 📚 Próximos Passos

Para evoluir este projeto:

1. **Adicionar autenticação** nos endpoints REST
2. **Implementar Dead Letter Queue (DLQ)** para mensagens com erro
3. **Adicionar retry automático** em caso de falha no processamento
4. **Implementar health checks** nos serviços
5. **Adicionar métricas** (Prometheus + Grafana)
6. **Criar testes automatizados**
7. **Implementar circuit breaker** para chamadas HTTP

---

## 👨‍💻 Autor

**Luiz Henrique**
- Projeto para disciplina de Microsserviços - IFBA
- Versão: 2.0-event-driven-simple

---

## 📄 Licença

Este projeto é educacional e de código aberto.
