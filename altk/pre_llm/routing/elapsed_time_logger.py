import logging
import sys
import asyncio
from functools import wraps
from time import perf_counter_ns


class ConsoleLogger:
    """Python Logging logger that logs the time it take to run a function.
    Taken from https://github.ibm.com/magma-platform/conversation-manager/blob/dev/src/common/console_logger.py
    """

    console_logger: logging.Logger | None = None

    @classmethod
    def get_logger(cls: type["ConsoleLogger"]):
        if not cls.console_logger:
            cls.console_logger = logging.getLogger(__name__)
            sh = logging.StreamHandler(sys.stdout)
            sh.setFormatter(
                logging.Formatter(
                    "%(levelname)s %(asctime)s [%(module)s/%(funcName)s] %(message)s"
                )
            )
            cls.console_logger.addHandler(sh)
            cls.console_logger.setLevel("DEBUG")
        return cls.console_logger


def processing_time_logger(logger):
    """
    Decorator function with input to log process time on sync and async methods for specific levels
    """

    def _processing_time_logger(func):
        def _get_module_name(module):
            """
            helper retrieving the module name from the given function by removing package names
            """

            moduleName = None
            if module is not None:
                moduleName = module.split(".")[-1]
            return moduleName

        def log_process_time(duration):
            """
            Actual logging of the duration along with functions module and name
            """

            moduleName = _get_module_name(func.__module__)
            functionName = func.__name__
            _logger = logger or ConsoleLogger.get_logger()
            _logger.log(
                logging.INFO,
                f"[{moduleName}/{functionName}] duration {duration / 1000000}ms",
            )

        @wraps(
            func
        )  # Required to work with fastapi router decorators, see https://stackoverflow.com/a/64656733
        def _processing_time_sync(*args, **kwargs):
            """
            Wrapper performing the time calculation and logging used for synchronously called methods
            """
            start = perf_counter_ns()
            result = func(*args, **kwargs)
            duration = perf_counter_ns() - start
            log_process_time(duration)
            return result

        @wraps(
            func
        )  # Required to work with fastapi router decorators, see https://stackoverflow.com/a/64656733
        async def _processing_time_async(*args, **kwargs):
            """
            Wrapper performing the time calculation and logging used for asynchronously called methods
            """
            start = perf_counter_ns()
            result = await func(*args, **kwargs)
            duration = perf_counter_ns() - start
            log_process_time(duration)
            return result

        # checking which method to serve based on async/await
        if asyncio.iscoroutinefunction(func):
            return _processing_time_async
        return _processing_time_sync

    return _processing_time_logger
