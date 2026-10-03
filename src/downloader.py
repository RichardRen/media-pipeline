import os.path

from adapter.db_operator import DbOperator
from adapter.mq_manager import MqManager
from adapter.system_invoker import SystemInvoker
from project.template_mq_consumer import MqConsumerTemplate
from utils.config import BaseConfig, MessageQueue
from utils.logger import setup_logger

logging = setup_logger(
    name="VideoDownloader",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "download.log")
)


class VideoDownloader(MqConsumerTemplate):
    def __init__(self, consume_queue, dead_queue, retry_field, publish_queue):
        self.publish_queue = publish_queue
        super().__init__(consume_queue, dead_queue, retry_field)

    def do_work(self, video_message):
        local_filename, channel_id = self.get_info_from_db(video_message)
        v_id = video_message.get("id")
        command = [
            "yt-dlp",
            "--verbose",
            "--continue",
            "--socket-timeout", "600", "--sleep-interval", "10", "--max-sleep-interval", "20",
            "--limit-rate", "2M",
            "--user-agent", "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/131.0.0.0 Safari/537.36",
            "--add-header", f"Referer: {os.path.join(BaseConfig.BASE_URL, channel_id, 'videos')}",
            "--write-thumbnail",
            "--convert-thumbnails", "png",
            "-f", "bestvideo[protocol^=http]+bestaudio[protocol^=http]", "--merge-output-format", "mp4",
            "-o", f"{local_filename}.mp4",
            f'{BaseConfig.VIDEO_URL}{v_id}'
        ]
        return SystemInvoker.system_invoke(command)

    @staticmethod
    def get_info_from_db(message):
        """
        查询视频存储路径
        """
        video_info = DbOperator.query_video_info_by_id(message.get("id"))
        return video_info.get('local_path'), video_info.get('channel_id')

    def after_success_process(self, video_message):
        v_id = video_message.get("id")
        DbOperator.update_vide_status_by_id(v_id, "downloaded")
        MqManager.push_message_to_channel(self.channel, self.publish_queue, video_message)


if __name__ == "__main__":
    # 启动 VideoDownloader 线程
    downloader = VideoDownloader(
        consume_queue=MessageQueue.MQ_TO_DOWNLOAD,
        dead_queue=MessageQueue.MQ_DEAD_DOWNLOAD,
        publish_queue=MessageQueue.MQ_TO_UPLOAD,
        retry_field="download_retries"
    )
    downloader.start()
    downloader.join()
