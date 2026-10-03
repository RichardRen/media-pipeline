import os


class MessageQueue:
    MQ_HOST = "localhost"
    MQ_HEARTBEAT = 60  # 十分钟心跳超时
    MQ_BLOCKED_CONNECTION_TIMEOUT = 120

    MQ_TO_DOWNLOAD = "video_to_download"
    MQ_TO_UPLOAD = "video_to_upload"
    MQ_TO_TRANSLATE = "video_to_translate"

    MQ_DEAD_DOWNLOAD = "dead_download_queue"
    MQ_DEAD_UPLOAD = "dead_upload_queue"
    MQ_DEAD_TRANSLATE = "dead_translate_queue"


class BaseConfig:
    BASE_URL = "https://www.youtube.com"
    VIDEO_URL = os.path.join(BASE_URL, "watch?v=")

    LOCAL_BASE_DIR = os.getenv("MEDIA_BASE_DIR", "/app/data")
    COOKIES_PATH = os.getenv("BILIUP_COOKIES_PATH", "/run/secrets/biliup_cookies.json")
