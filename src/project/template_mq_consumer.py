import json
import logging
import threading
import time
from abc import ABC, abstractmethod
from threading import Thread

from pika.exceptions import StreamLostError, AMQPConnectionError

from adapter.mq_manager import MqManager


class MqConsumerTemplate(ABC, Thread):

    def __init__(self, consume_queue, dead_queue, retry_field):
        self.job_name = type(self).__name__
        super().__init__(name=f"{self.job_name}-Thread")
        self.consume_queue = consume_queue
        self.dead_queue = dead_queue
        # self.publish_queue = publish_queue
        self.retry_field = retry_field
        self.connection = None
        self.channel = None

    def run(self):
        logging.info(f"consumer {self.job_name} started...")
        try:
            self.connection = MqManager.connect_rabbitmq()
            self.channel = self.connection.channel()
            self.channel.queue_declare(queue=self.consume_queue, durable=True)
            self.channel.basic_qos(prefetch_count=1)

            def send_heartbeat(connection):
                """在独立线程中发送心跳"""
                while connection.is_open:
                    time.sleep(30)  # 每30s发送一次
                    connection.process_data_events()
                    logging.info(f"consumer {self.job_name} heartbeat sent.")

            heartbeat_thread = threading.Thread(target=send_heartbeat, args=(self.connection,))
            heartbeat_thread.daemon = True
            heartbeat_thread.start()

            def callback(ch, method, properties, body):
                if not self.consumer_retry_control(body):
                    logging.error(f"consumer {self.job_name} failed and requeue for next time")
                    self.channel.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
                    return
                logging.info(f"consumer {self.job_name} success and ack")
                self.channel.basic_ack(delivery_tag=method.delivery_tag)

            self.channel.basic_consume(queue=self.consume_queue, on_message_callback=callback, auto_ack=False)
            logging.info(f"Starting to consume one message out of {self.consume_queue} queue")
            self.channel.start_consuming()
        except StreamLostError as e:
            logging.error(f"Stream connection lost: {e}.")
        except AMQPConnectionError as e:
            logging.error(f"RabbitMQ connection error: {e}.")
        except Exception as e:
            logging.error(f"Unexpected error in consume_queue: {e}.")
        finally:
            if self.connection and self.connection.is_open:
                self.connection.close()
            logging.info("Connection closed, and exit.")

    def consumer_retry_control(self, body):
        video_message = json.loads(body)
        retries = int(video_message.get(self.retry_field))
        if retries >= 3:
            MqManager.push_message_to_channel(self.channel, self.dead_queue, video_message)
            logging.error(f"video: {video_message} download retries is: {retries} times, pushed to dead queue")
            return True

        # 下载失败
        if not self.do_work(video_message):
            retries = retries + 1
            video_message[self.retry_field] = retries
            logging.error(f"video: {video_message} download failed, append download_retries to {retries} times")
            return False

        # 下载成功，更新数据库状态，推送到下一队列
        self.after_success_process(video_message)
        return True

    @abstractmethod
    def do_work(self, video_message):
        pass

    @abstractmethod
    def after_success_process(self, video_message):
        pass
