# Microsserviços de Futebol - Arquitetura Orientada a Eventos

Sistema de gerenciamento de jogos de futebol, comentários e votos usando **arquitetura event-driven** com **RabbitMQ**.

## 🎥 Vídeo Explicativo
[Assistir vídeo no YouTube](https://youtu.be/RFR7ClFlA1M)

---

## 🏗️ Arquitetura Event-Driven

### O que é Arquitetura Orientada a Eventos?

Ao invés dos microsserviços se comunicarem **diretamente via HTTP** (REST), eles se comunicam **indiretamente via mensagens** através de um **message broker** (RabbitMQ).

**Vantagens:**
- 🔌 **Desacoplamento:** Serviços não conhecem uns aos outros
- 🛡️ **Resiliência:** Mensagens não se perdem se um serviço cair
- 📈 **Escalabilidade:** Fácil adicionar múltiplos consumidores
- ⚡ **Assíncrono:** Não bloqueia esperando resposta

### Como Funciona?

```
┌──────────┐     eventos      ┌──────────┐     eventos      ┌──────────┐
│ Crawler  │ ──────────────> │ RabbitMQ │ ──────────────> │ Serviços │
│ Client   │ <────────────── │  Broker  │ <────────────── │  (3)     │
└──────────┘    respostas    └──────────┘    respostas    └──────────┘
```

**Fluxo:**
1. **Publicador** (Crawler/Client) envia **evento** para RabbitMQ
2. RabbitMQ roteia evento para **fila** correta
3. **Consumidor** (Serviço) processa evento da fila
4. Serviço confirma processamento (ACK) ou rejeita (NACK)

---

## 📬 Sistema de Filas e Exchanges

### Exchanges (Pontos de Entrada)

| Exchange | Tipo | Função |
|----------|------|--------|
| `futebol.commands` | direct | Recebe **comandos** (criar jogo, comentário, voto) |
| `futebol.queries` | direct | Recebe **consultas** (listar jogos, comentários, votos) |
| `futebol.events` | fanout | **Transmite eventos** para múltiplos serviços (pub/sub) |

### Filas (Destino das Mensagens)

**Filas de Comando** (Write Operations):
```
futebol.commands ──┬──> jogos.command.criar         → Serviço Jogos
                   ├──> comentarios.command.criar   → Serviço Comentários
                   └──> votacao.command.criar       → Serviço Votação
```

**Filas de Consulta** (Read Operations - RPC):
```
futebol.queries ───┬──> jogos.query.listar          → Serviço Jogos
                   ├──> comentarios.query.listar    → Serviço Comentários
                   └──> votacao.query.listar        → Serviço Votação
```

**Filas de Eventos** (Pub/Sub):
```
futebol.events ────┬──> comentarios.events.jogo     → Serviço Comentários
(jogo.registrado)  └──> votacao.events.jogo         → Serviço Votação
```

### 3 Padrões de Mensageria Implementados

#### 1️⃣ **Work Queue** (Fila de Trabalho)
- **Uso:** Criar jogos, comentários e votos
- **Como funciona:** Evento vai para **uma fila**, **um consumidor** processa
- **Exemplo:** `jogo.criar` → Fila `jogos.command.criar` → Serviço Jogos processa

#### 2️⃣ **Pub/Sub** (Publicar/Subscrever)
- **Uso:** Notificar quando um jogo é registrado
- **Como funciona:** Evento vai para **todos os subscritores** (fanout)
- **Exemplo:** Jogos publica `jogo.registrado` → Comentários **e** Votação recebem

#### 3️⃣ **RPC** (Request-Reply)
- **Uso:** Consultas que precisam de resposta
- **Como funciona:** Cliente envia query com `correlation_id` e aguarda resposta
- **Exemplo:** Client pede jogos → Serviço responde com lista de jogos

---

## 🚀 Como Executar (Primeira Vez)

### Pré-requisitos
- **Docker** e **Docker Compose** instalados
- **Python 3** instalado

### Passo 1: Subir os Serviços

```bash
# Clone ou navegue até o diretório do projeto
cd futebol-event-driven

# Suba todos os containers (RabbitMQ + 3 serviços + 3 Memcached)
docker-compose up --build -d

# Aguarde ~10 segundos para RabbitMQ inicializar completamente
sleep 10
```

**O que foi iniciado:**
- ✅ RabbitMQ (ports 5672 e 15672)
- ✅ Serviço Jogos
- ✅ Serviço Comentários
- ✅ Serviço Votação
- ✅ 3 instâncias Memcached

### Passo 2: Verificar se está Funcionando

```bash
# Ver logs dos serviços (deve mostrar "pronto para receber eventos")
docker logs jogos
docker logs comentarios
docker logs votacao

# Acessar interface web do RabbitMQ
# Abra no navegador: http://localhost:15672
# Usuário: admin | Senha: admin
```

Na interface RabbitMQ, vá em **Queues** - você deve ver todas as filas criadas.

### Passo 3: Instalar Dependências Python

```bash
# Criar ambiente virtual
python3 -m venv venv

# Ativar ambiente virtual
source venv/bin/activate  # Linux/Mac
# OU
venv\Scripts\activate     # Windows

# Instalar dependências
pip install -r requirements.txt
```

### Passo 4: Popular Dados Iniciais

```bash
# Executar crawler para publicar eventos de jogos, comentários e votos
python3 crawler.py --once

# O crawler irá:
# 1. Ler arquivos data/*.json
# 2. Publicar eventos no RabbitMQ
# 3. Serviços processarão automaticamente
```

**Saída esperada:**
```
Conectando ao RabbitMQ...
Conexão estabelecida e publisher configurado
--- Iteração 1 ---
Evento publicado: jogo.criar - Bahia vs Vitoria
Evento publicado: jogo.criar - Flamengo vs Vasco
2 jogos publicados com sucesso
✓ Jogos publicados
...
```

### Passo 5: Usar o Cliente Interativo

```bash
# Executar cliente CLI
python3 client.py
```

**Menu do Cliente:**
```
╔════════════════════════════════════════════════════════════╗
║     ⚽ FUTEBOL MICROSERVICES - EVENT-DRIVEN CLI           ║
╠════════════════════════════════════════════════════════════╣
║  1. 📋 Listar jogos e detalhes                            ║
║  2. 💬 Adicionar comentário                               ║
║  3. 🗳️  Adicionar voto                                     ║
║  4. 🚪 Sair                                                ║
╚════════════════════════════════════════════════════════════╝
Escolha uma opção:
```

**Teste:**
1. Escolha `1` para listar jogos
2. Digite ID do jogo (ex: `1`) para ver comentários e votos
3. Escolha `2` para adicionar comentário
4. Escolha `3` para adicionar voto

---

## 📊 Visualizar Mensagens no RabbitMQ

1. Acesse http://localhost:15672 (admin/admin)
2. Clique em **Queues**
3. Clique em uma fila (ex: `jogos.command.criar`)
4. Veja estatísticas: mensagens processadas, consumidores ativos, etc.
5. Use **"Publish message"** para testar envio manual

---

## 🔧 Comandos Úteis

```bash
# Ver logs em tempo real
docker logs -f jogos

# Parar todos os serviços
docker-compose down

# Reiniciar após alterações
docker-compose down
docker-compose up --build -d

# Executar crawler continuamente (a cada 10s)
python3 crawler.py

# Executar crawler apenas uma vez
python3 crawler.py --once
```

---

## 🏛️ Estrutura dos Serviços

### Serviço de Jogos
- **Consome:** `jogo.criar`, `query.jogos`
- **Publica:** `jogo.registrado`
- **Armazena:** Memcached (banco_jogos)

### Serviço de Comentários
- **Consome:** `comentario.criar`, `query.comentarios`, `jogo.registrado`
- **Publica:** `comentario.registrado`
- **Armazena:** Memcached (banco_comentarios)

### Serviço de Votação
- **Consome:** `voto.criar`, `query.votacao`, `jogo.registrado`
- **Publica:** `voto.registrado`
- **Armazena:** Memcached (banco_votacao)

---

## 🆚 REST vs Event-Driven

| Característica | REST | Event-Driven |
|----------------|------|--------------|
| Comunicação | Síncrona (HTTP) | Assíncrona (Mensagens) |
| Acoplamento | Alto (conhece URLs) | Baixo (via broker) |
| Resiliência | Falha se serviço down | Mensagens persistem |
| Escalabilidade | Horizontal (load balancer) | Múltiplos consumidores |
| Rastreamento | Logs distribuídos | Broker centraliza |

---

## 📚 Conceitos Demonstrados

✅ Arquitetura Orientada a Eventos
✅ Message Broker (RabbitMQ)
✅ Work Queues
✅ Publish/Subscribe (Fanout)
✅ RPC Pattern (Request-Reply)
✅ Manual Acknowledgment
✅ Dead Letter Queues (DLQ)
✅ Desacoplamento de Serviços
✅ Comunicação Assíncrona

---

## 🐛 Troubleshooting

**Problema:** Client não conecta ao RabbitMQ
- **Solução:** Verifique se RabbitMQ está rodando: `docker ps | grep rabbitmq`

**Problema:** Serviços não processam eventos
- **Solução:** Veja logs: `docker logs jogos` - procure por erros

**Problema:** Filas não aparecem no RabbitMQ UI
- **Solução:** Serviços criam filas ao iniciar. Reinicie: `docker-compose restart`

**Problema:** Crawler dá erro de conexão
- **Solução:** Aguarde RabbitMQ inicializar completamente (~10s após `docker-compose up`)

---

## 👨‍💻 Desenvolvido para

Disciplina de **Microsserviços** - IFBA
Demonstração de arquitetura event-driven com RabbitMQ

---

## 📖 Resumo Rápido

1. **Clone/navegue** até o projeto
2. **Execute** `docker-compose up --build -d`
3. **Aguarde** 10 segundos
4. **Ative** venv: `source venv/bin/activate`
5. **Instale** deps: `pip install -r requirements.txt`
6. **Popule** dados: `python3 crawler.py --once`
7. **Use** cliente: `python3 client.py`
8. **Monitore** RabbitMQ: http://localhost:15672 (admin/admin)

**Pronto!** 🎉
