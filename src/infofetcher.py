import json
import os
import re
from threading import Thread
from typing import List

from adapter.db_operator import DbOperator
from adapter.mq_manager import MqManager
from adapter.system_invoker import SystemInvoker
from modules.infos import ChannelInfo
from utils.config import BaseConfig, MessageQueue
from utils.logger import setup_logger

logging = setup_logger(
    name="VideoInfoFetcher",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "fetchinfo.log")
)


class MyAppError(Exception):
    """项目中的基类异常"""
    pass


class VideoInfoFetcher(Thread):

    def __init__(self, channel_info):
        super().__init__(name="VideoInfoFetcher-Thread")
        self.channel_info = channel_info

    def run(self):
        """

        :return:
        """

        try:
            # 保存上传者信息到数据库
            self.save_channel_info_to_db()
            # 获取全量视频信息
            video_info_lst: List = self.download_video_list_info()
            # 保存视频信息列表到数据库
            self.save_video_info_lst_to_db(video_info_lst)
            # 组装message，推送到视频元数据到RabbitMQ
            self.push_to_rabbitmq(video_info_lst)
        except Exception as e:
            logging.info(f"Exception is: {e}")

    def save_channel_info_to_db(self):
        DbOperator.insert_channel_info(self.channel_info)
        # 创建channel本地目录
        channel_dir = os.path.join(BaseConfig.LOCAL_BASE_DIR, self.channel_info.channel)
        os.makedirs(channel_dir, exist_ok=True)

    def download_video_list_info(self):
        command = [
            "yt-dlp",
            "--flat-playlist",
            "-j",
            "--extractor-args", "youtube:tab=max_videos=10000",
            os.path.join(BaseConfig.BASE_URL, self.channel_info.channel_id, "videos")
        ]
        # logging.info(f"command: {command}")
        result = SystemInvoker.system_invoke_result(command)
        if result.returncode != 0:
            logging.error(f"system invoke failed, command:{command}")
            raise MyAppError(f"system invoke failed, command:{command}")

        # 创建channel本地目录
        # channel_dir = os.path.join(BaseConfig.LOCAL_BASE_DIR, self.channel_info.channel)
        # os.makedirs(channel_dir, exist_ok=True)

        video_infos = self.parse_all_channel_data(result)
        if not video_infos:
            logging.error(f"parse video infos failed")
            raise MyAppError(f"parse video infos failed")

        return video_infos

    def parse_all_channel_data(self, result):
        videos = []
        for line in result.stdout.splitlines():
            video_data = self.load_json_data(line)
            if not video_data or video_data["_type"] != "url":
                logging.error(f"video data: {video_data} is not valid")
                return []
            videos.append(self.parse_video_details(video_data))
        return videos

    @staticmethod
    def load_json_data(data):
        try:
            video_data = json.loads(data)
            return video_data
        except json.JSONDecodeError or TypeError as e:
            logging.error(f"Error decoding JSON: {e}")
            return []

    def parse_video_details(self, video_data):
        try:
            id = video_data.get("id")
            url = video_data.get("url")
            title = self.sanitize_filepath(video_data.get("title"))
            description = self.sanitize_filepath(video_data.get("description"))
            playlist_uploader = self.sanitize_filepath(video_data.get("playlist_uploader"))
            playlist_uploader_id = self.sanitize_filepath(video_data.get("playlist_uploader_id"))
            duration = video_data.get("duration")
            duration_string = video_data.get("duration_string")
            view_count = video_data.get("view_count")
            playlist = self.sanitize_filepath(video_data.get("playlist"))
            playlist_id = video_data.get("playlist_id")
            playlist_title = self.sanitize_filepath(video_data.get("playlist_title"))
            playlist_index = video_data.get("playlist_index")
            last_playlist_index = video_data.get("__last_playlist_index")

            # 定制上传bili的英文title、description、上传下载使用的本地文件名前缀
            # bili_title = f'[{self.channel_info.channel}]{title}'[:80]
            # bili_desc = f'[{self.channel_info.channel}]{title}\n{url}\n{description}'
            # local_path_name = f'{title}'[:80]
            # local_path = os.path.join(channel_dir, local_path_name)

            return {
                "id": id,
                "url": url,
                "title": title,
                # "title_bili": bili_title,
                "description": description,
                # "description_bili": bili_desc,
                "status": "fetched",
                "uploader": playlist_uploader,
                "uploader_id": playlist_uploader_id,
                "channel": self.channel_info.channel,
                "channel_id": self.channel_info.channel_id,
                "duration": duration,
                "duration_string": duration_string,
                "view_count": view_count,
                "playlist": playlist,
                "playlist_id": playlist_id,
                "playlist_title": playlist_title,
                "playlist_index": playlist_index,
                "last_playlist_index": last_playlist_index
                # "local_path": local_path
            }
        except Exception as e:
            logging.error(f"Error in parse video infos: {e}")
            return {}

    @staticmethod
    def save_video_info_lst_to_db(video_info_lst):
        for video in video_info_lst:
            DbOperator.insert_video_info(video)  # in db oper need try catch

    @staticmethod
    def push_to_rabbitmq(video_info_lst):
        connection = MqManager.connect_rabbitmq()
        channel = connection.channel()
        for video_info in video_info_lst:
            message = {"id": video_info.get("id"), "title": video_info.get("title"), "download_retries": 0,
                       "translate_retries": 0, "upload_retries": 0}
            MqManager.push_message_to_channel(channel, MessageQueue.MQ_TO_TRANSLATE, message)
        connection.close()

    @staticmethod
    def sanitize_filepath(name_str):
        """
        去除文件名中的非法字符
        """
        if name_str is None:
            return ""
        sanitized = re.sub(r'[\/:*?"<>|\']', '', name_str)
        sanitized = sanitized.strip()
        return sanitized


if __name__ == "__main__":
    # 启动 VideoInfoFetcher 线程
    # infofetcher = VideoInfoFetcher(ChannelInfo('@annabel.lucinda', 'Annabel Lucinda'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@sallymcraestrength', 'Sally McRae'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@brookewellss', 'Brooke Wells'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@kellylmatthews', 'Strong With Kelly'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@MattieRogersWeightlifting', 'Mattie Rogers'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@micawood', 'Mica Rivera Wood'))
    # infofetcher = VideoInfoFetcher(ChannelInfo('@doclyssfitness', 'Doc Lyss Fitness'))
    infofetcher = VideoInfoFetcher(ChannelInfo('@KrissyCelaa', 'Krissy Cela'))

    infofetcher.start()
    infofetcher.join()
