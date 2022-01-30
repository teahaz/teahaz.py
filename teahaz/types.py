"""The module containing the common types used by the library."""

from typing import Callable, Union, Any, Dict

import requests

from .dataclasses import Message

MessageCallback = Callable[[Message], Any]

ErrorCallback = Callable[
    [requests.Response, str, Dict[str, Any]],
    Any,
]

ExceptionCallback = Callable[
    [Exception, str, Dict[str, Any]],
    Any,
]

EventCallback = Union[MessageCallback, ErrorCallback]
