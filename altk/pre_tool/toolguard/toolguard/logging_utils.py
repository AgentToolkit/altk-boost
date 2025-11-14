import logging


def add_log_file_handler(log_file: str):
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logging.getLogger().addHandler(file_handler)


def init_logging():
    logging.getLogger().setLevel(logging.INFO)  # Default for other libraries
    logging.getLogger("toolguard").setLevel(logging.DEBUG)  # debug for our library
    logging.getLogger("mellea").setLevel(logging.DEBUG)
    init_log_console_handler()


def init_log_console_handler():
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # Set up the root logger
    logging.basicConfig(level=logging.INFO, handlers=[console_handler])
