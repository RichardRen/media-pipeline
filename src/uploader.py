import os.path
import time

from adapter.db_operator import DbOperator
from adapter.system_invoker import SystemInvoker
from project.template_mq_consumer import MqConsumerTemplate
from utils.config import BaseConfig, MessageQueue
from utils.logger import setup_logger

logging = setup_logger(
    name="VideoUploader",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "upload.log")
)


class VideoUploader(MqConsumerTemplate):

    def __init__(self, consume_queue, dead_queue, retry_field):
        self.local_filename = ""
        super().__init__(consume_queue, dead_queue, retry_field)

    def do_work(self, video_message):
        bili_title, bili_desc, self.local_filename = self.get_info_from_db(video_message)
        command = [ # https://github.com/biliup/biliup-rs
            "biliup",
            "-u", BaseConfig.COOKIES_PATH,
            "upload", f"{self.local_filename}.mp4",  # self.video_path
            "--tag", "运动,体育,短片",
            "--tid", "238",  # TAGS = "运动,体育,短片"
            "--title", bili_title,
            "--desc", bili_desc,
            "--cover", f"{self.local_filename}.png"
        ]
        return SystemInvoker.system_invoke(command)

    @staticmethod
    def get_info_from_db(message):
        """
        获取视频上传相关参数
        """
        video_info = DbOperator.query_video_info_by_id(message.get('id'))
        return video_info.get('title_bili'), video_info.get('description_bili'), video_info.get('local_path')

    def after_success_process(self, video_message):
        v_id = video_message.get("id")
        DbOperator.update_vide_status_by_id(v_id, "uploaded")
        # 删除本地源文件
        if os.path.exists(f"{self.local_filename}.mp4"):
            os.remove(f"{self.local_filename}.mp4")
        if os.path.exists(f"{self.local_filename}.png"):
            os.remove(f"{self.local_filename}.png")
        time.sleep(40)


if __name__ == "__main__":
    # 启动 VideoUploader 线程
    downloader = VideoUploader(
        consume_queue=MessageQueue.MQ_TO_UPLOAD,
        dead_queue=MessageQueue.MQ_DEAD_UPLOAD,
        # publish_queue=None,
        retry_field="upload_retries")
    downloader.start()
    downloader.join()
