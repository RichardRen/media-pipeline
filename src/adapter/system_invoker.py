import os
import subprocess

from utils.config import BaseConfig
from utils.logger import setup_logger

logging = setup_logger(
    name="SystemInvoker",
    log_file=os.path.join(BaseConfig.LOCAL_BASE_DIR, "logs", "system_invoker.log")
)


class SystemInvoker:

    @staticmethod
    def system_invoke(command):
        logging.info(f"command invoke: {command}")
        try:
            process = subprocess.Popen(
                command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            # 实时读取子进程输出，避免缓冲区溢出
            for line in process.stdout:
                logging.info(line.strip())
            stdout, stderr = process.communicate()
            if process.returncode != 0:
                logging.error(f"Failed to command invoke, err: {stderr}, command: {command}")
                return False
            logging.info(f"Video downloaded successfully, command: {command}")
            return True
        except Exception as e:
            logging.error(f"Exception during command invoke, err: {e}, command: {command}")
            return False

    @staticmethod
    def system_invoke_result(command):
        logging.info(f"command invoke: {command}")
        try:
            result = subprocess.run(command, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return result
        except subprocess.CalledProcessError as e:
            logging.error(f"Error running yt-dlp: {e.stderr}, command: {command}")
            return None
        except Exception as e:
            logging.error(f"Exception during command invoke, err: {e}, command: {command}")
            return None
