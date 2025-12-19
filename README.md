# Projeto de Microsserviços de Futebol - Arquitetura Orientada a Eventos

Este projeto demonstra uma **arquitetura de microsserviços orientada a eventos** para gerenciar informações de jogos de futebol, comentários e votos. Ele consiste em três microsserviços principais (`jogos`, `comentarios` e `votacao`) que se comunicam através de eventos usando **RabbitMQ** como message broker.

## Vídeo Explicativo
[Clique aqui para assistir o vídeo](https://youtu.be/RFR7ClFlA1M)

---

## Arquitetura

### Visão Geral

Este projeto implementa uma arquitetura orientada a eventos onde os microsserviços se comunicam de forma **assíncrona** através de mensagens no RabbitMQ, ao invés de usar chamadas HTTP síncronas.

```
┌─────────────┐
│   Crawler   │
│  (Cliente)  │
└──────┬──────┘
       │ publica eventos
       ▼
┌─────────────────────────────────────┐
│           RabbitMQ                  │
│  ┌─────────────────────────────┐   │
│  │ Exchanges & Queues          │   │
│  │ - futebol.commands (direct) │   │
│  │ - futebol.queries (direct)  │   │
│  │ - futebol.events (fanout)   │   │
│  └─────────────────────────────┘   │
└──────┬──────────┬──────────┬────────┘
       │          │          │
       ▼          ▼          ▼
┌──────────┐ ┌─────────┐ ┌─────────┐
│  Jogos   │ │Comentar.│ │ Votacao │
│ Service  │ │ Service │ │ Service │
└────┬─────┘ └────┬────┘ └────┬────┘
     │            │           │
     ▼            ▼           ▼
┌──────────┐ ┌─────────┐ ┌─────────┐
│banco_jogos│banco_com.│banco_vot.│
│(Memcached)│(Memcached)│(Memcached)│
└──────────┘ └─────────┘ └─────────┘
```

### Principais Diferenças da Arquitetura REST

| Aspecto | REST (Anterior) | Event-Driven (Atual) |
|---------|----------------|----------------------|
| **Comunicação** | HTTP síncrono | Mensagens assíncronas (RabbitMQ) |
| **Acoplamento** | Serviços conhecem URLs uns dos outros | Serviços desacoplados via broker |
| **Protocolo** | REST/JSON sobre HTTP | AMQP/JSON sobre RabbitMQ |
| **Padrão** | Request-Response | Pub/Sub + RPC + Work Queues |
| **Resiliência** | Falha imediata se serviço está down | Mensagens ficam na fila até processamento |

---

## Microsserviços

### 1. Serviço de Jogos
Gerencia informações de jogos de futebol (jogos passados e futuros).

**Eventos Consumidos:**
- `jogo.criar` - Cria ou atualiza informações de um jogo
- `query.jogos` - Consulta todos os jogos (padrão RPC)

**Eventos Publicados:**
- `jogo.registrado` - Notifica outros serviços que um jogo foi armazenado

**Armazenamento:** Memcached (`banco_jogos`)

### 2. Serviço de Comentários
Gerencia comentários para jogos específicos.

**Eventos Consumidos:**
- `comentario.criar` - Adiciona um comentário a um jogo
- `query.comentarios` - Consulta comentários de um jogo (padrão RPC)
- `jogo.registrado` - Recebe notificações de novos jogos (validação)

**Eventos Publicados:**
- `comentario.registrado` - Confirma que um comentário foi armazenado

**Armazenamento:** Memcached (`banco_comentarios`)

### 3. Serviço de Votação
Gerencia votos sobre qual time vencerá um jogo futuro.

**Eventos Consumidos:**
- `voto.criar` - Adiciona um voto a um jogo
- `query.votacao` - Consulta votos de um jogo (padrão RPC)
- `jogo.registrado` - Recebe notificações de novos jogos (validação)

**Eventos Publicados:**
- `voto.registrado` - Confirma que um voto foi armazenado

**Armazenamento:** Memcached (`banco_votacao`)

---

## RabbitMQ - Exchanges e Filas

### Exchanges

| Exchange | Tipo | Propósito |
|----------|------|-----------|
| `futebol.commands` | direct | Roteia comandos (criar jogos, comentários, votos) |
| `futebol.queries` | direct | Roteia consultas (listar jogos, comentários, votos) |
| `futebol.events` | fanout | Transmite eventos de domínio (jogo.registrado) |

### Filas

**Comandos:**
- `jogos.command.criar` - Criação de jogos
- `comentarios.command.criar` - Criação de comentários
- `votacao.command.criar` - Criação de votos

**Consultas (RPC):**
- `jogos.query.listar` - Listagem de jogos
- `comentarios.query.listar` - Listagem de comentários por jogo
- `votacao.query.listar` - Listagem de votos por jogo

**Eventos:**
- `comentarios.events.jogo` - Recebe notificações de jogos registrados
- `votacao.events.jogo` - Recebe notificações de jogos registrados

---

## Padrões de Mensageria Implementados

### 1. Work Queues (Filas de Trabalho)
Comandos são distribuídos para os serviços consumirem e processarem.

### 2. Publish/Subscribe (Fanout)
Quando um jogo é registrado, o evento `jogo.registrado` é transmitido para todos os serviços interessados (Comentários e Votação).

### 3. RPC (Request-Reply)
Consultas funcionam como chamadas RPC:
1. Cliente envia uma mensagem de consulta com `reply_to` e `correlation_id`
2. Serviço processa e responde na fila de resposta
3. Cliente recebe a resposta correlacionada

---

## Configuração e Execução do Projeto

### Pré-requisitos
- Docker e Docker Compose instalados
- Python 3 e `pip` (para executar `crawler.py` e `client.py`)

### 1. Construir e Executar Serviços com Docker Compose

Navegue até o diretório raiz do projeto e execute:

```bash
docker-compose up --build -d
```

Este comando irá:
- Construir imagens Docker para os serviços `jogos`, `comentarios` e `votacao`
- Baixar a imagem do RabbitMQ com interface de gerenciamento
- Baixar as imagens `memcached` para os bancos de dados
- Iniciar todos os serviços em modo `detached`

### 2. Acessar a Interface de Gerenciamento do RabbitMQ

O RabbitMQ Management UI estará disponível em:

```
http://localhost:15672
```

**Credenciais:**
- Usuário: `admin`
- Senha: `admin`

Através desta interface você pode:
- Visualizar exchanges, filas e bindings
- Monitorar mensagens em tempo real
- Enviar mensagens de teste manualmente
- Ver estatísticas de consumo e publicação

### 3. Popular Dados (usando Crawler)

O script `crawler.py` lê os dados iniciais dos arquivos JSON em `data/` e os **publica como eventos** no RabbitMQ.

Primeiro, certifique-se de ter as dependências Python instaladas:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Em seguida, execute o crawler:

```bash
python3 crawler.py
```

O crawler irá:
1. Conectar-se ao RabbitMQ
2. Publicar eventos `jogo.criar` para cada jogo em `data/jogos.json`
3. Publicar eventos `comentario.criar` para cada comentário em `data/comentarios.json`
4. Publicar eventos `voto.criar` para cada voto em `data/votacao.json`

### 4. Usando o Cliente Python

O script `client.py` fornece uma interface de linha de comando interativa que usa o **padrão RPC** para consultas e **fire-and-forget** para comandos.

```bash
python3 client.py
```

O cliente permite:
- Listar todos os jogos (RPC)
- Adicionar comentários a um jogo (fire-and-forget)
- Adicionar votos a um jogo (fire-and-forget)
- Listar comentários de um jogo (RPC)
- Listar votos de um jogo (RPC)

---

## Estrutura do Projeto

```
futebol-event-driven/
├── app/
│   ├── messaging/               # Camada de mensageria compartilhada
│   │   ├── __init__.py
│   │   ├── rabbitmq_client.py   # Conexão, Publisher, Consumer, RPC
│   │   └── events.py            # Schemas de eventos
│   ├── jogos/
│   │   └── servico.py           # Serviço de jogos (event consumer)
│   ├── comentarios/
│   │   └── servico.py           # Serviço de comentários (event consumer)
│   └── votacao/
│       └── servico.py           # Serviço de votação (event consumer)
├── data/                        # Dados iniciais JSON
│   ├── jogos.json
│   ├── comentarios.json
│   └── votacao.json
├── crawler.py                   # Carrega dados publicando eventos
├── client.py                    # Cliente CLI com RPC
├── docker-compose.yml           # Orquestração dos serviços
├── Dockerfile                   # Imagem base dos serviços
├── requirements.txt             # Dependências Python
└── README.md                    # Este arquivo
```

---

## Confiabilidade e Tratamento de Erros

### Acknowledgment Manual
Todos os consumidores usam **manual acknowledgment**:
- ✅ ACK: Mensagem processada com sucesso
- ❌ NACK com requeue: Erro transitório (ex: DB temporariamente indisponível)
- ❌ NACK sem requeue: Erro permanente → Dead Letter Queue

### Dead Letter Queues (DLQ)
Mensagens que falharam após múltiplas tentativas são enviadas para DLQs:
- `jogos.command.criar.dlq`
- `comentarios.command.criar.dlq`
- `votacao.command.criar.dlq`

### Retry Logic
- Máximo de 3 tentativas para erros transitórios
- Backoff exponencial entre tentativas
- Após esgotadas as tentativas → DLQ

---

## Conceitos de Microsserviços Demonstrados

Este projeto é uma ferramenta educacional que demonstra:

✅ **Arquitetura Orientada a Eventos** - Comunicação assíncrona via eventos
✅ **Message Broker** - RabbitMQ como intermediário de mensagens
✅ **Desacoplamento de Serviços** - Serviços não conhecem uns aos outros
✅ **Work Queues** - Distribuição de trabalho entre consumidores
✅ **Publish/Subscribe** - Broadcasting de eventos (fanout)
✅ **RPC Pattern** - Request-reply assíncrono para consultas
✅ **Resiliência** - Mensagens persistem na fila se serviço estiver down
✅ **Escalabilidade** - Múltiplos consumidores podem processar a mesma fila
✅ **Dead Letter Queues** - Tratamento de falhas permanentes
✅ **Event-Driven Domain Events** - Eventos de domínio (jogo.registrado)

---

## Desenvolvimento

### Modificando Serviços

Após fazer alterações em qualquer arquivo, reconstrua os containers:

```bash
docker-compose down
docker-compose up --build -d
```

### Visualizando Logs

Para ver os logs de um serviço específico:

```bash
docker logs -f jogos
docker logs -f comentarios
docker logs -f votacao
docker logs -f rabbitmq
```

### Testando Manualmente com RabbitMQ UI

1. Acesse http://localhost:15672
2. Vá para a aba "Queues"
3. Selecione uma fila (ex: `jogos.command.criar`)
4. Use "Publish message" para enviar eventos de teste
5. Observe os logs do serviço para ver o processamento

---

## Ambiente Virtual Python

É recomendado usar um ambiente virtual Python para gerenciar as dependências:

```bash
python3 -m venv venv
source venv/bin/activate  # No Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Desative o ambiente virtual quando terminar:

```bash
deactivate
```

---

## Monitoramento

### RabbitMQ Management UI
- **URL:** http://localhost:15672
- **Features:**
  - Visualização de filas e profundidade
  - Taxa de mensagens por segundo
  - Consumidores ativos
  - Histórico de mensagens

### Logs dos Serviços
Cada serviço loga:
- Eventos recebidos
- Processamento iniciado
- Sucesso/falha
- ACK/NACK decisions

---

## Comparação: REST vs Event-Driven

### Vantagens da Arquitetura Orientada a Eventos

✅ **Desacoplamento:** Serviços não precisam conhecer a localização uns dos outros
✅ **Resiliência:** Mensagens não são perdidas se um serviço está offline
✅ **Escalabilidade:** Fácil adicionar múltiplos consumidores para uma fila
✅ **Assíncrono:** Não bloqueia esperando resposta (exceto em RPC)
✅ **Auditoria:** RabbitMQ mantém histórico de mensagens
✅ **Flexibilidade:** Novos serviços podem subscrever eventos existentes

### Quando Usar Cada Abordagem

**REST/HTTP:**
- APIs públicas
- Comunicação síncrona necessária
- Operações CRUD simples
- Clientes web/mobile

**Event-Driven:**
- Comunicação entre microsserviços internos
- Processamento assíncrono
- Workflows complexos
- Necessidade de auditoria e replay

---

## Autor

Projeto desenvolvido para a disciplina de **Microsserviços** do curso de Sistemas de Informação do IFBA.

## Licença

Este projeto é open source e está disponível para fins educacionais.
