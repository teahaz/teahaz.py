"""The module containing the common types used by the library."""

from __future__ import annotations

from typing import Callable, Union, Any

import requests

from .dataclasses import Message

MessageCallback = Callable[[Message], Any]

ErrorCallback = Callable[
    [requests.Response, str, dict[str, Any]],
    Any,
]

ExceptionCallback = Callable[
    [Exception, str, dict[str, Any]],
    Any,
]

EventCallback = Union[MessageCallback, ErrorCallback]
