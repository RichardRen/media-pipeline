import json
import os
from time import sleep

import pika
from pika.exceptions import AMQPConnectionError

from utils.config import MessageQueue, BaseConfig
from utils.logger import setup_logger

logging = setup_logger(
    name="MqManager",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "mq_manager.log")
)


class MqManager:

    def __init__(self):
        pass

    @staticmethod
    def connect_rabbitmq():
        """
        建立 RabbitMQ 连接
        """
        # while not stop_event.is_set():
        mq_host = os.getenv("MQ_HOST", "rabbitmq")
        mq_port = int(os.getenv("MQ_PORT", "5672"))
        try:
            credentials = pika.PlainCredentials(
                os.getenv("MQ_USER", "user"),
                os.environ["MQ_PASSWORD"]
            )
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=mq_host,
                    port=mq_port,
                    credentials=credentials,
                    heartbeat=MessageQueue.MQ_HEARTBEAT,
                    blocked_connection_timeout=MessageQueue.MQ_BLOCKED_CONNECTION_TIMEOUT  # 根据需要调整
                )
            )
            logging.info("已连接到 RabbitMQ。")
            return connection
        except AMQPConnectionError as e:
            logging.error(f"连接 RabbitMQ 失败: {e}. 5 秒后重试...")
            sleep(5)
        except Exception as e:
            logging.error(f"连接 RabbitMQ 时发生意外错误: {e}. 5 秒后重试...")
            sleep(5)

    @staticmethod
    def push_message_to_channel(channel, queue_name, message):
        channel.queue_declare(queue=queue_name, durable=True)

        channel.basic_publish(
            exchange='',
            routing_key=queue_name,
            body=json.dumps(message),
            properties=pika.BasicProperties(delivery_mode=2)
        )
        logging.info(f"Pushed to MQ, channel: {channel}, queue_name:{queue_name}, message:{message}")
