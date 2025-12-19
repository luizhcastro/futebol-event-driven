import pika
import json
import uuid
import os
import logging
import time
import threading
from typing import Callable, Dict, Any, Optional

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RabbitMQConnection:
    """Gerencia conexão com RabbitMQ com reconexão automática"""

    def __init__(self, host=None, user=None, password=None):
        self.host = host or os.getenv('RABBITMQ_HOST', 'localhost')
        self.user = user or os.getenv('RABBITMQ_USER', 'admin')
        self.password = password or os.getenv('RABBITMQ_PASS', 'admin')
        self.connection = None
        self.channel = None

    def connect(self, max_retries=10, retry_delay=5):
        """Conecta ao RabbitMQ com retry"""
        retries = 0
        while retries < max_retries:
            try:
                credentials = pika.PlainCredentials(self.user, self.password)
                parameters = pika.ConnectionParameters(
                    host=self.host,
                    credentials=credentials,
                    heartbeat=600,
                    blocked_connection_timeout=300
                )
                self.connection = pika.BlockingConnection(parameters)
                self.channel = self.connection.channel()
                logger.info(f"Conectado ao RabbitMQ em {self.host}")
                return self.channel
            except Exception as e:
                retries += 1
                logger.error(f"Erro ao conectar ao RabbitMQ (tentativa {retries}/{max_retries}): {e}")
                if retries < max_retries:
                    logger.info(f"Aguardando {retry_delay}s antes de tentar novamente...")
                    time.sleep(retry_delay)
                else:
                    raise Exception(f"Falha ao conectar ao RabbitMQ após {max_retries} tentativas")

    def close(self):
        """Fecha a conexão"""
        try:
            if self.channel and self.channel.is_open:
                self.channel.close()
            if self.connection and self.connection.is_open:
                self.connection.close()
            logger.info("Conexão com RabbitMQ fechada")
        except Exception as e:
            logger.error(f"Erro ao fechar conexão: {e}")


class EventPublisher:
    """Publica eventos para exchanges"""

    def __init__(self, connection: RabbitMQConnection):
        self.connection = connection
        self.channel = connection.channel

    def declare_exchange(self, exchange_name: str, exchange_type: str = 'direct'):
        """Declara um exchange"""
        self.channel.exchange_declare(
            exchange=exchange_name,
            exchange_type=exchange_type,
            durable=True
        )
        logger.info(f"Exchange '{exchange_name}' ({exchange_type}) declarado")

    def publish(self, exchange: str, routing_key: str, message: Dict[str, Any],
                properties: Optional[pika.BasicProperties] = None):
        """Publica uma mensagem"""
        try:
            body = json.dumps(message, ensure_ascii=False)

            if properties is None:
                properties = pika.BasicProperties(
                    delivery_mode=2,  # mensagem persistente
                    content_type='application/json'
                )

            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=properties
            )
            logger.info(f"Evento publicado: {routing_key} -> {exchange}")
            logger.debug(f"Payload: {message}")

        except Exception as e:
            logger.error(f"Erro ao publicar evento: {e}")
            raise


class EventConsumer:
    """Consome eventos de filas com acknowledgment manual"""

    def __init__(self, connection: RabbitMQConnection):
        self.connection = connection
        self.channel = connection.channel
        self.handlers = {}

    def declare_queue(self, queue_name: str, durable: bool = True,
                     arguments: Optional[Dict] = None):
        """Declara uma fila"""
        self.channel.queue_declare(
            queue=queue_name,
            durable=durable,
            arguments=arguments
        )
        logger.info(f"Fila '{queue_name}' declarada")

    def bind_queue(self, queue_name: str, exchange: str, routing_key: str):
        """Faz bind de uma fila a um exchange"""
        self.channel.queue_bind(
            queue=queue_name,
            exchange=exchange,
            routing_key=routing_key
        )
        logger.info(f"Fila '{queue_name}' vinculada a '{exchange}' com routing_key '{routing_key}'")

    def subscribe(self, queue_name: str, callback: Callable):
        """Registra um handler para uma fila"""
        self.handlers[queue_name] = callback

    def start_consuming(self):
        """Inicia o consumo de mensagens"""
        for queue_name, callback in self.handlers.items():
            self.channel.basic_qos(prefetch_count=1)
            self.channel.basic_consume(
                queue=queue_name,
                on_message_callback=self._create_callback_wrapper(callback),
                auto_ack=False  # acknowledgment manual
            )
            logger.info(f"Consumindo fila: {queue_name}")

        logger.info("Iniciando consumo de mensagens...")
        try:
            self.channel.start_consuming()
        except KeyboardInterrupt:
            logger.info("Consumo interrompido pelo usuário")
            self.channel.stop_consuming()
        except Exception as e:
            logger.error(f"Erro durante consumo: {e}")
            raise

    def _create_callback_wrapper(self, user_callback: Callable):
        """Cria um wrapper para o callback do usuário com tratamento de erros"""
        def callback_wrapper(ch, method, properties, body):
            try:
                logger.info(f"Mensagem recebida: {method.routing_key}")
                message = json.loads(body)
                logger.debug(f"Payload: {message}")

                # Chama o handler do usuário
                user_callback(ch, method, properties, message)

                # ACK se processado com sucesso
                ch.basic_ack(delivery_tag=method.delivery_tag)
                logger.info(f"Mensagem processada com sucesso: {method.delivery_tag}")

            except json.JSONDecodeError as e:
                logger.error(f"Erro ao decodificar JSON: {e}")
                # NACK sem requeue para mensagens inválidas
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

            except Exception as e:
                logger.error(f"Erro ao processar mensagem: {e}")
                # NACK com requeue para erros transitórios
                ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

        return callback_wrapper


class RPCClient:
    """Cliente RPC para requisições request-reply"""

    def __init__(self, connection: RabbitMQConnection):
        self.connection = connection
        self.channel = connection.channel
        self.callback_queue = None
        self.responses = {}

        # Cria fila de resposta exclusiva
        result = self.channel.queue_declare(queue='', exclusive=True)
        self.callback_queue = result.method.queue

        # Registra callback para respostas (sem auto_ack para melhor controle)
        self.channel.basic_consume(
            queue=self.callback_queue,
            on_message_callback=self._on_response,
            auto_ack=True
        )

    def _on_response(self, ch, method, properties, body):
        """Callback para respostas RPC"""
        try:
            if properties.correlation_id in self.responses:
                self.responses[properties.correlation_id] = json.loads(body)
                logger.debug(f"RPC response armazenada: {properties.correlation_id}")
        except Exception as e:
            logger.error(f"Erro ao processar resposta RPC: {e}")

    def call(self, exchange: str, routing_key: str, message: Dict[str, Any],
             timeout: int = 10) -> Optional[Dict]:
        """Faz uma chamada RPC e aguarda resposta"""
        correlation_id = str(uuid.uuid4())
        self.responses[correlation_id] = None

        try:
            body = json.dumps(message, ensure_ascii=False)

            # Publica requisição
            self.channel.basic_publish(
                exchange=exchange,
                routing_key=routing_key,
                body=body,
                properties=pika.BasicProperties(
                    reply_to=self.callback_queue,
                    correlation_id=correlation_id,
                    content_type='application/json',
                    delivery_mode=1  # non-persistent para RPC
                )
            )

            logger.info(f"RPC call: {routing_key} [correlation_id: {correlation_id}]")

            # Aguarda resposta processando eventos
            start_time = time.time()
            while self.responses[correlation_id] is None:
                if time.time() - start_time > timeout:
                    logger.error(f"Timeout na chamada RPC: {routing_key}")
                    self.responses.pop(correlation_id, None)
                    return None

                # Processa eventos de I/O (isso irá chamar _on_response quando houver resposta)
                try:
                    self.connection.connection.process_data_events(time_limit=0.1)
                except Exception as e:
                    logger.error(f"Erro ao processar eventos: {e}")
                    self.responses.pop(correlation_id, None)
                    return None

            response = self.responses.pop(correlation_id)
            logger.info(f"RPC response recebida [correlation_id: {correlation_id}]")
            return response

        except Exception as e:
            logger.error(f"Erro em chamada RPC: {e}")
            self.responses.pop(correlation_id, None)
            return None


class RPCServer:
    """Servidor RPC para processar requisições e enviar respostas"""

    def __init__(self, consumer: EventConsumer):
        self.consumer = consumer

    def register_rpc_handler(self, queue_name: str, handler: Callable):
        """Registra um handler RPC que deve retornar a resposta"""
        def rpc_callback(ch, method, properties, message):
            try:
                # Processa a requisição
                response = handler(message)

                # Envia resposta
                if properties.reply_to:
                    ch.basic_publish(
                        exchange='',
                        routing_key=properties.reply_to,
                        body=json.dumps(response, ensure_ascii=False),
                        properties=pika.BasicProperties(
                            correlation_id=properties.correlation_id,
                            content_type='application/json'
                        )
                    )
                    logger.info(f"RPC response enviada [correlation_id: {properties.correlation_id}]")

            except Exception as e:
                logger.error(f"Erro em handler RPC: {e}")
                # Envia resposta de erro se possível
                if properties.reply_to:
                    error_response = {"error": str(e)}
                    ch.basic_publish(
                        exchange='',
                        routing_key=properties.reply_to,
                        body=json.dumps(error_response, ensure_ascii=False),
                        properties=pika.BasicProperties(
                            correlation_id=properties.correlation_id
                        )
                    )

        self.consumer.subscribe(queue_name, rpc_callback)
