# Resumo da Simplificação - Event-Driven Architecture

## 🎯 Objetivo
Simplificar a implementação event-driven para ficar no mesmo nível de complexidade do projeto Kafka (giftcard), mantendo os conceitos de arquitetura orientada a eventos.

## 📊 Comparação: Antes vs Depois

### Antes (Implementação Complexa)
- **Linhas de código**: ~1.200 linhas totais
- **Arquivos**: 11 arquivos
- **Abstrações**: Classes complexas (RabbitMQConnection, EventPublisher, EventConsumer, RPCClient, RPCServer)
- **Pasta messaging**: ~350 linhas de código de infraestrutura
- **Padrões**: RPC, Exchanges (direct, fanout), Routing keys complexos
- **Cliente**: RPC com correlation IDs e filas exclusivas

### Depois (Implementação Simples)
- **Linhas de código**: ~600 linhas totais (50% redução)
- **Arquivos**: 7 arquivos (removidos 4 da pasta messaging)
- **Abstrações**: Chamadas diretas ao Pika
- **Pasta messaging**: REMOVIDA ❌
- **Padrões**: Work Queues simples
- **Cliente**: REST API com requests

## 🔧 Mudanças Principais

### 1. Removida Pasta `/app/messaging/`
```
❌ /app/messaging/rabbitmq_client.py (122 linhas)
❌ /app/messaging/events.py (95 linhas)
❌ /app/messaging/__init__.py (38 linhas)
```

### 2. Serviço de Jogos (`app/jogos/servico.py`)
**Antes**: 220 linhas com classes complexas
**Depois**: 170 linhas com código direto

**Mudanças**:
- ✅ Flask REST API mantida
- ✅ Chamadas diretas ao `pika` (sem abstrações)
- ✅ APScheduler para consumir fila "jogos" a cada 3s
- ✅ Publica para fila "jogos_eventos" após armazenar

**Fluxo**:
```
POST /jogos → publica para fila "jogos"
         ↓
APScheduler (3s) → consome "jogos" → armazena Memcached → publica "jogos_eventos"
```

### 3. Serviço de Comentários (`app/comentarios/servico.py`)
**Antes**: 244 linhas com RPC e eventos
**Depois**: 134 linhas com REST + consumer simples

**Mudanças**:
- ✅ Flask REST API (GET/POST /comentarios)
- ✅ APScheduler para consumir "jogos_eventos" a cada 3s
- ✅ Armazena comentários no Memcached

### 4. Serviço de Votação (`app/votacao/servico.py`)
**Antes**: 244 linhas com RPC e eventos
**Depois**: 134 linhas com REST + consumer simples

**Mudanças**:
- ✅ Flask REST API (GET/POST /votacao)
- ✅ APScheduler para consumir "jogos_eventos" a cada 3s
- ✅ Armazena votos no Memcached

### 5. Crawler (`crawler.py`)
**Antes**: 219 linhas com eventos complexos
**Depois**: 126 linhas com publicação simples

**Mudanças**:
- ✅ Publica jogos diretamente na fila "jogos" com `basic_publish`
- ✅ Remove comentários e votos (serão adicionados via client.py)

### 6. Client (`client.py`)
**Antes**: 312 linhas com RPC pattern
**Depois**: 236 linhas com REST simples

**Mudanças**:
- ✅ Usa biblioteca `requests` para chamadas HTTP
- ✅ Endpoints REST: `localhost:5001`, `localhost:5002`, `localhost:5003`
- ❌ Remove RPC, correlation IDs, filas exclusivas

### 7. Docker Compose
**Mudanças**:
- ✅ Adicionadas portas 5001, 5002, 5003 aos serviços
- ❌ Removido volume `./app/messaging:/app/messaging`
- ❌ Removidas variáveis RABBITMQ_USER e RABBITMQ_PASS

## 🔄 Arquitetura Event-Driven Simplificada

```
┌─────────────┐
│  Crawler    │
└──────┬──────┘
       │ publica
       ↓
   ┌────────────────┐
   │ Fila "jogos"   │
   └────────┬───────┘
            │ consome (APScheduler 3s)
            ↓
   ┌─────────────────────┐
   │  Serviço Jogos      │
   │  - Armazena no DB   │
   │  - Publica evento   │
   └──────────┬──────────┘
              │ publica
              ↓
   ┌──────────────────────┐
   │ Fila "jogos_eventos" │
   └───────┬──────────────┘
           │ consome (APScheduler 3s)
     ┌─────┴─────┐
     ↓           ↓
┌──────────┐  ┌──────────┐
│Comentários│  │ Votação  │
│          │  │          │
│REST APIs │  │REST APIs │
└────┬─────┘  └─────┬────┘
     │              │
     └──────┬───────┘
            │ HTTP GET/POST
            ↓
      ┌──────────┐
      │ Client   │
      └──────────┘
```

## 📋 Padrões Utilizados

### 1. Work Queues (Filas de Trabalho)
- Fila `jogos`: Distribuição de trabalho
- Fila `jogos_eventos`: Notificação de eventos

### 2. Polling com APScheduler
- Executado a cada 3 segundos
- `basic_get()` para buscar mensagens
- Manual acknowledgment com `basic_ack()`

### 3. REST API
- Client comunica com serviços via HTTP
- Endpoints simples: GET e POST

## 🎓 Conceitos Mantidos

Mesmo simplificado, o projeto ainda demonstra:
- ✅ Arquitetura Orientada a Eventos
- ✅ Message Broker (RabbitMQ)
- ✅ Desacoplamento entre serviços
- ✅ Comunicação assíncrona
- ✅ Persistência de mensagens (durable queues)
- ✅ Manual acknowledgment

## 🚀 Como Executar

```bash
# 1. Subir os serviços
docker-compose up --build

# 2. Executar o crawler (em outro terminal)
python3 crawler.py --once

# 3. Executar o client
python3 client.py
```

## 📦 Dependências

```
flask
requests
pymemcache
pika>=1.3.0
flask_apscheduler
```

## ✅ Benefícios da Simplificação

1. **Mais fácil de entender**: Código direto, sem abstrações
2. **Mais fácil de debugar**: Menos camadas de código
3. **Mais didático**: Similar ao projeto Kafka de referência
4. **Menos código**: 50% de redução
5. **Mesmos conceitos**: Event-driven mantido

## 🔍 Diferenças do Projeto Kafka

| Aspecto | Kafka (giftcard) | RabbitMQ (futebol) |
|---------|------------------|---------------------|
| Biblioteca | `confluent_kafka` | `pika` |
| Consumer | `consumer.poll()` | `basic_get()` |
| Producer | `producer.produce()` | `basic_publish()` |
| Polling | APScheduler | APScheduler |
| Complexidade | Simples | Simples |

---

**Data da Simplificação**: 2025-12-19
**Versão**: 2.0-event-driven-simple
