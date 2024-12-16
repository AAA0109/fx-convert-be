from enum import Enum
from typing import Callable, Optional, Union

# Logging.
from django.core.exceptions import ObjectDoesNotExist
from hdlib.AppUtils.log_util import get_logger, logging

logger = get_logger(level=logging.INFO)


def get_or_none(func: Callable):
    """
    Wrapper function which either returns the output of a function if no exception is raised, or None if
    an exception is raised
    :param func: Callable, the function to wrap
    :return: Callable, wrapped function
    """

    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ObjectDoesNotExist:
            return None

    return wrapper


class ActionStatus(object):
    """
    Class to record actions taken at the (hedge) account level, and the corresponding status
    """

    class Status(Enum):
        SUCCESS = "SUCCESS"
        ERROR = "ERROR"
        NO_CHANGE = "NO_CHANGE"

        def __str__(self) -> str:
            return self.value

    def __init__(self, status: Status, message: str = "", code: Union[int, str] = None):
        """
        :param status: Status, the status code for the action
        :param message: str, a message describing in more detail what occured
        :param code: int (optional), ability to set specific error codes for handling downstream
        """
        self.status = status
        self.message = message
        self.code: Optional[int] = code

    def __str__(self) -> str:
        return f"{self.status}: {self.message}"

    def is_success(self) -> bool:
        return self.status == ActionStatus.Status.SUCCESS

    def is_error(self) -> bool:
        return self.status == ActionStatus.Status.ERROR

    def is_no_change(self) -> bool:
        return self.status == ActionStatus.Status.NO_CHANGE

    def set_code(self, code: Union[int, str] = None) -> 'ActionStatus':
        self.code = code
        return self

    @classmethod
    def success(cls, message: Optional[str] = None):
        return ActionStatus(ActionStatus.Status.SUCCESS,
                            message=message or "Success")

    @classmethod
    def log_and_success(cls, message: Optional[str] = None):
        if message:
            logger.debug(message)
        return ActionStatus.success(f"STATUS SUCCESS: {message}")

    @classmethod
    def error(cls, message: Optional[str] = None, code: Union[int, str] = None):
        return ActionStatus(ActionStatus.Status.ERROR,
                            message=message or "Error",
                            code=code)

    @classmethod
    def log_and_error(cls, message: Optional[str] = None, code: int = None):
        if message:
            logger.error(message)
        return ActionStatus.error(f"Error: {message}")

    @classmethod
    def no_change(cls, message: Optional[str] = None):
        return ActionStatus(ActionStatus.Status.NO_CHANGE,
                            message=message or "No Change")

    @classmethod
    def log_and_no_change(cls, message: Optional[str] = None):
        if message:
            logger.debug(message)
        return ActionStatus.no_change(message)
