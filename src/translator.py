import json
import os
import time

from openai import OpenAI

from adapter.db_operator import DbOperator
from adapter.mq_manager import MqManager
from project.template_mq_consumer import MqConsumerTemplate
from utils.config import BaseConfig, MessageQueue
from utils.logger import setup_logger

logging = setup_logger(
    name="VideoTranslator",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "translator.log")
)


class VideoTranslator(MqConsumerTemplate):

    def __init__(self, consume_queue, dead_queue, retry_field, publish_queue):
        self.publish_queue = publish_queue
        self.title_zh = ""
        self.title_bili = ""
        self.description_zh = ""
        self.description_bili = ""
        self.local_path = ""
        super().__init__(consume_queue, dead_queue, retry_field)

    def do_work(self, video_message):
        url, channel, title, description = self.get_info_from_db(video_message)
        video = {
            # "id": video_message.get("id"),
            "title": title,
            "description": description
        }
        result = json.loads(self.invoke_openai(video))
        logging.info(f"result: {result}")
        # result = json.loads(result)
        self.title_zh = result.get("title")
        self.description_zh = result.get("description")

        # 生成title_bili，description_bili，local_path
        self.title_bili = f'[{channel}]{self.title_zh}'[:80]
        self.description_bili = f'欢迎反馈互动，谢谢三连充电！\n{channel}\n{self.description_zh}\n{title}\n{description}\n{url.replace("/", "")}'
        self.local_path = os.path.join(BaseConfig.LOCAL_BASE_DIR, channel, f'{self.title_zh}'[:80])
        return True

    def get_info_from_db(self, message):
        video_info = DbOperator.query_video_info_by_id(message.get("id"))
        return video_info.get('url'), video_info.get('channel'), video_info.get('title'), video_info.get('description')

    def invoke_openai(self, video):
        # OpenAI SDK reads OPENAI_API_KEY from the process environment.
        client = OpenAI()
        # 构造批量输入的 Prompt
        # prompts = []
        # for i, video in enumerate(videos):
        # prompts.append(video)

        # 合并所有视频内容到一个 Prompt
        prompt = f"""only translate the following titles and descriptions from English to Chinese.
        Make the translation natural, engaging, and suitable for YouTube content, including slang, fitness terms, and internet expressions.
        The output must be in the same JSON structure as the input, and all keys must remain unchanged.
        Input:
        {json.dumps(video, ensure_ascii=False, indent=4)}
        """
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful translator."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=2000,  # 控制输出长度
        )
        return completion.choices[0].message.content.strip()

    def after_success_process(self, video_message):
        DbOperator.update_vide_status_by_id(video_message.get("id"), "translated")
        DbOperator.update_translated_content_by_id(video_message.get("id"), self.title_zh, self.description_zh,
                                                   self.title_bili, self.description_bili, self.local_path)
        MqManager.push_message_to_channel(self.channel, self.publish_queue, video_message)
        time.sleep(10)


if __name__ == "__main__":
    translator = VideoTranslator(
        consume_queue=MessageQueue.MQ_TO_TRANSLATE,
        dead_queue=MessageQueue.MQ_DEAD_TRANSLATE,
        publish_queue=MessageQueue.MQ_TO_DOWNLOAD,
        retry_field="translate_retries"
    )
    translator.start()
    translator.join()
