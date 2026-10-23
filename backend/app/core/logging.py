import logging
import sys

#mục đích: nhằm ghi lại quá trình PDF parsing, chunking, embedding và lỗi dịch vụ mà không làm lộ API key hoặc nội dung nhạy cảm.
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
#log_format thống nhất cấu trúc cho mọi log 
def configure_logging(log_level: str = "INFO") -> None:
    """Configure logging for application modules."""

    app_logger = logging.getLogger("app")
    app_logger.setLevel(log_level)
    app_logger.propagate = False

    if app_logger.handlers:
        return

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    app_logger.addHandler(console_handler)