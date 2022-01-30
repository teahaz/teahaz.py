"""The module containing the main objects for the Teahaz API wrapper."""

# pylint: disable=too-many-instance-attributes

from __future__ import annotations

from enum import Enum, auto
from threading import Thread
from time import sleep, time as epoch
from base64 import b64encode, b64decode
from typing import Callable, Any, Union

import requests

from .dataclasses import (
    User,
    Invite,
    Channel,
    Message,
)

from .types import EventCallback

__all__ = [
    "Event",
    "Teacup",
    "Chatroom",
]


class Event(Enum):
    """Events that `Chatroom` and `Teacup` can subscribe to"""

    ERROR = auto()
    """An error occured.

    Args:
        response: The `requests.Response` object.
        method: The HTTP method used.
        request_args: A dictionary of arguments sent with the request.
    """

    MSG_NEW = auto()
    """A new message has arrived.

    Args:
        message: The new `Message` instance.
    """

    MSG_DEL = auto()
    """A message was deleted.

    Args:
        message: The deleted `Message` instance.
    """

    MSG_SYS = auto()
    """A system message has arrived.

    Args:
        message: The system message.
    """

    MSG_SENT = auto()
    """A message has been sent.

    This can be used by clients to show the outgoing message,
    before the server receives and sends it back.

    Args:
        message: The **locally instanced** `Message`. Only use this while the real
            message has not yet arrived.
    """

    USER_JOIN = auto()
    """A new user has joined the chatroom.

    Note:
        **Not yet implemented.**
    """

    USER_LEAVE = auto()
    """A user has left the chatroom.

    Note:
        **Not yet implemented.**
    """

    SERVER_INFO = auto()
    """Some server information has changed.

    Note:
        **Not yet implemented.**
    """

    MSG_SYS_SILENT = auto()
    """A silent system message has arrived. These should normally not be displayed.

    Note:
        **Not yet implemented.**
    """

    NETWORK_EXCEPTION = auto()
    """A network exception has occured.

    Note:
        **Not yet implemented.**
    """


class EndpointContainer:
    """Contains the endpoints of the Teahaz API."""

    _items = {
        "base": "{url}/api/v0",
        "login": "{base}/login/{chatroom_id}",
        "chatroom": "{base}/chatroom",
        "files": "{base}/files/{chatroom_id}",
        "messages": "{base}/messages/{chatroom_id}",
        "channels": "{base}/channels/{chatroom_id}",
        "invites": "{base}/invites/{chatroom_id}",
    }

    def __init__(self, url: str, uid: str | None = None) -> None:
        """Initializes object.

        Args:
            url: The URL to use.
            uid: The chatroom uid to use.
        """

        self.url = url
        self.uid = uid

    def list(self) -> list[str]:
        """Returns a list of all endpoints."""

        return [getattr(self, key) for key in self._items]

    def __getattr__(self, item: str) -> str:
        """Gets a formatted endpoint.

        Args:
            item: The endpoint key.
        """

        # This is a special key
        if item == "base":
            return self._items["base"].format(url=self.url)

        return self._items[item].format(
            url=self.url, base=self.base, chatroom_id=self.uid
        )


class Chatroom:
    """The object to deal with all chatroom-related API actions."""

    def __init__(
        self,
        url: str,
        uid: str | None = None,
        name: str | None = None,
        session: requests.Session | None = None,
    ) -> None:
        """Initializes chatroom.

        Args:
            url: The chatroom's server URL:PORT.
            uid: The chatroom's UUID.
            name: The display name of the chatroom.
            session: Session that should be used by this chatroom.

        Every argument except URL is optional. This object should usually
        be instanced within the module, not by outside code.
        """

        self.uid = uid
        self.url = url
        self.name = name
        self.interval = 1

        self.username: str | None = None
        self.session = session or requests.Session()
        self.active_channel: Channel | None = None
        self.channels: list[Channel] = []

        self.event_thread = Thread(target=self._loop)

        # If the chatroom doesn't exist yet its endpoints' uid
        # is only filled in the create() method
        self.endpoints = EndpointContainer(self.url, self.uid)

        self.messages: list[Message] = []

        self._listeners: dict[Event, EventCallback] = {}
        self._is_looping: bool = False
        self._is_stopped: bool = False
        self._is_server_side: bool = False
        self._last_get_time: float = epoch()

    def _request(self, method_name: str, **req_args: Any) -> Any | None:
        """Sends a request, handles events & exceptions.

        Args:
            method_name: An HTTP method name, such as GET.
            **req_args: Arguments passed to the request.

        Returns:
        - JSON of response if `status_code == 200`
        - None if exception occured but was handled

        Raises:
            ValueError: Invalid HTTP method was passed.
            RuntimeError: Response status_code was not 200, and
                no handler was available to call.
        """

        method = getattr(self.session, method_name)
        if method is None:
            raise ValueError(f'Session does not have a method for "{method_name}".')

        error_handler = self._listeners.get(Event.ERROR)
        exception_handler = self._listeners.get(Event.NETWORK_EXCEPTION)

        try:
            response = method(**req_args)
        except Exception as exception:
            # This should just raise a custom Exception.
            if exception_handler is not None:
                exception_handler(exception, method_name, req_args)  # type: ignore

                # maybe this could return CapturedException/CapturedError?
                return None

            raise exception

        if response.status_code == 200:
            return response.json()

        if error_handler is not None:
            error_handler(response, method_name, req_args)  # type: ignore

            # maybe this could return CapturedError?
            return None

        raise RuntimeError(
            f"{method_name.upper()} request with data {req_args} failed"
            f" with no error or exception handler: {response.status_code} -> {response.text}"
        )

    def _notify(self, event: Event, *data: Any) -> None:
        """Notifies listeners of an event.

        Args:
            event: The event to notify for.
            *data: Any arguments passed to the listeners.
        """

        callback = self._listeners.get(event)
        if callback is None:
            return

        callback(*data)

    def _loop(self) -> None:
        """The main event loop for a chatroom"""

        ids = [msg.uid for msg in self.messages]
        self._last_get_time = epoch()

        while not self._is_stopped:
            if self.active_channel is None:
                sleep(self.interval)
                continue

            # We need to assign to a temporary
            # variable, otherwise messages can
            # get stuck between setting & getting.
            previous = self._last_get_time
            self._last_get_time = epoch()
            messages = self.get_since(previous)

            if messages is not None:
                # there is no good way to type these
                messages.sort(key=lambda msg: msg.send_time)

                for message in messages:
                    # This is needed to avoid duplicates
                    if message.uid in ids:
                        continue

                    self.messages.append(message)
                    ids.append(message.uid)

                    if message.message_type == "delete":
                        self._notify(Event.MSG_DEL, message)

                    elif message.message_type == "system":
                        self._notify(Event.MSG_SYS, message)

                    elif message.message_type == "system-silent":
                        self._notify(Event.MSG_SYS_SILENT, message)

                    else:
                        self._notify(Event.MSG_NEW, message)

            sleep(self.interval)

    def _run(self) -> None:
        """Runs monitoring loop"""

        self._is_looping = True
        self.event_thread.start()
        self._update_thread_name()

    def _initialize_from_response(self, response: dict) -> None:
        """Initializes data of chatroom from a response dict.

        Args:
            response: A dictionary of Teahaz server response.
        """

        self.name = response["chatroom_name"]
        self.uid = response["chatroomID"]
        self.username = response["users"][0]["username"]

        assert self.uid is not None
        self.endpoints.uid = self.uid
        self._update_thread_name()

        self._update_channels(
            [Channel.from_dict(channel) for channel in response["channels"]]
        )
        self._is_server_side = True

    def _update_channels(self, channels: list[Channel] | None = None) -> None:
        """Updates channels available to the user."""

        assert self.username, "Please log in before getting channels!"

        if channels is None:
            channels = self.get_channels()
            if channels is None:
                return

        for channel in channels:
            if channel not in self.channels:
                self.channels.append(channel)

        if self.active_channel is None and len(self.channels) > 0:
            self.active_channel = self.channels[0]

    def _update_thread_name(self) -> None:
        """Sets self.event_thread.name."""

        self.event_thread.name = f'Chatroom(uid="{self.uid}")'

    def _get_messages(
        self,
        method: str,
        channel: Channel | None = None,
        count: str | None = None,
        time: str | None = None,
    ) -> list[Message] | None:
        """Gets messages by time (since) or count.

        Args:
            method: `time` or `count`.
            channel: The channel to get messages from.
            count: How many messages to get. Only used when `method=="count"`.
            time: The time to get messages since.
        """

        if channel is not None:
            self.active_channel = channel

        elif self.active_channel is None:
            raise ValueError(
                "Please use either the Chatroom.set_channel() function"
                + " or provide `channel` as a non-null value!"
            )

        else:
            channel = self.active_channel

        headers = {
            "get-method": method,
            "username": self.username,
            "channelID": channel.uid,
            "count": count,
            "time": time,
        }

        messages: list[dict[str, Any]] | None = self._request(
            "get",
            url=self.endpoints.messages,
            headers=headers,
        )

        if messages is None:
            # Getting messages failed, but error was captured
            return None

        instances = []
        for message in messages:
            if not message["type"].startswith("system"):
                message["data"] = self._decrypt(message["data"])

            instances.append(Message.from_dict(message))

        return instances

    @staticmethod
    def _encrypt(message: bytes) -> str:
        """Encrypts the given message.

        Note:
            As encryption is currently not supported by the server, all this function does
            is b64encode the given string.

        Args:
            message: Text to encrypt.

        Returns:
            The encrypted text.
        """

        return b64encode(message).decode("ascii")

    @staticmethod
    def _decrypt(message: bytes) -> str:
        """Decrypts the given message.

        Note:
            As encryption is currently not supported by the server, all this function does
            is b64decode the given string.

        Args:
            message: Text to decrypt.

        Returns:
            The decrypted text.
        """

        return b64decode(message).decode("ascii")

    def subscribe(self, event: Event, callback: EventCallback) -> None:
        """Start listening for and event and run callback when it occurs.

        Sideeffect:
            This method will call `self._run()` if the event passed is not an
            Error or NetworkException.
        """

        self._listeners[event] = callback

        if not self._is_looping and not event in [Event.ERROR, Event.NETWORK_EXCEPTION]:
            self._run()

    def stop(self) -> None:
        """Stops event loop."""

        self._is_stopped = True

    def create(self, username: str, password: str) -> Chatroom | None:
        """Creates a new chatroom on the server.

        Args:
            username: The owner account's username.
            password: The owner account's password.

        Returns:
            This chatroom, logged into the given owner account.
        """

        data = {
            "chatroom-name": self.name,
            "username": username,
            "password": password,
        }

        response = self._request(
            "post",
            headers={"Content-Type": "application/json"},
            url=self.endpoints.chatroom,
            json=data,
        )

        if response is None:
            # Creation did not succeed, but error was captured
            return None

        self._initialize_from_response(response)
        return self

    def create_channel(self, name: str) -> Channel | None:
        """Creates a channel.

        Args:
            name: The display name for the new channel.

        Returns:
            The new channel object in case of success, None otherwise.
        """

        data = {
            "username": self.username,
            "channel-name": name,
            "permissions": [{"classID": "1", "r": True, "w": True, "x": False}],
        }

        response = self._request("post", url=self.endpoints.channels, json=data)

        if response is None:
            # Creation of chatroom failed, but error was captured
            return None

        channel = Channel.from_dict(response)
        self._update_channels([channel])

        return channel

    def create_invite(
        self, uses: int = 1, expiration_time: float | None = None
    ) -> Invite | None:
        """Creates an invite to this chatroom.

        Args:
            uses: How many times this invite can be used.
            expiration_time: Epoch float describing when the invite will no
                longer be valid.

        Returns:
            Invite object in case of success, None otherwise.
        """

        headers = {
            "username": self.username,
        }

        if uses is not None:
            headers["uses"] = str(uses)

        if expiration_time is not None:
            headers["expiration-time"] = str(expiration_time)

        response = self._request("get", url=self.endpoints.invites, headers=headers)

        if response is None:
            return None

        response["url"] = self.url
        response["chatroomID"] = self.uid
        return Invite.from_dict(response)

    def create_from_invite(
        self, invite: Invite, username: str, password: str
    ) -> Chatroom | None:
        """Initializes chatroom from an invite.

        Args:
            invite: The invite object to use.
            username: The username of the account registered using this invite.
            password: The password of the account registered using this invite.

        Returns:
            This chatroom instance logged into the user on success, None otherwise.
        """

        data = {
            "inviteID": invite.uid,
            "username": username,
            "password": password,
        }

        response = self._request("post", url=self.endpoints.invites, json=data)

        if response is None:
            return None

        self._initialize_from_response(response)

        return self

    def get_users(self) -> list[User] | None:
        """Gets all users in a chatroom.

        Returns:
            A list of User instances on success, None otherwise.
        """

        users = self._request(
            "get",
            data={"username": self.uid},
        )

        if users is None:
            # Getting users failed, but error was captured
            return None

        return [User.from_dict(user) for user in users]

    def get_channels(self) -> list[Channel] | None:
        """Gets all channels the logged-in user has access to.

        Returns:
            A list of Channel instances on success, None otherwise.
        """

        channels = self._request(
            "get",
            url=self.endpoints.channels,
            headers={"username": self.username},
        )

        if channels is None:
            # Getting channels failed, but error was captured
            return None

        return [Channel.from_dict(channel) for channel in channels]

    def login(self, username: str, password: str) -> requests.Response | None:
        """Logs into the chatroom with given credentials.

        Args:
            username: Username to log into.
            password: Password to log in with.

        Returns:
            Raw response for some reason.
        """

        data = {
            "username": username,
            "password": password,
        }

        response = self._request(
            "post",
            url=self.endpoints.login,
            json=data,
        )

        if response is None:
            return None

        self.username = username
        self._update_channels()
        self._is_server_side = True

        return response

    def get_since(
        self, since: float, channel: Channel | None = None
    ) -> list[Message] | None:
        """Gets messages since provided timestamp.

        Args:
            since: UNIX epoch timestamp from which to get messages.
            channel: The optional channel to filter messages by.

        Returns:
            A list of messages on success, None otherwise.
        """

        return self._get_messages(
            "since",
            channel,
            time=str(since),
        )

    def get_count(
        self, count: int, channel: Channel | None = None
    ) -> list[Message] | None:
        """Gets a certain count of messages sent since provided timestamp.

        Args:
            count: The maximum amount of messages returned.
            channel: The channel to filter messages by.

        Returns:
            A list of messages on success, None otherwise.
        """

        return self._get_messages(
            "count",
            channel,
            str(count),
        )

    def send(
        self,
        content: Union[str, bytes],
        channel: Channel | None = None,
        reply_id: str | None = None,
    ) -> None:
        """Sends a message.

        Args:
            content: Message data. Currently only `str` is supported.
            channel: The channel to send the message on. Defaults to self.active_channel.
            reply_id: The optional id of the messages this one will reply to.

        Returns:
            None. The outgoing message can be acquired by subscribing to `Event.MSG_SENT`.

        Raises:
            ValueError: No channel was passed, and self.active_channel is None.

        Sideeffect:
            This changes self.active_channel to the provided one, if it isn't None.
        """

        msg = {}
        if channel is not None:
            self.active_channel = channel

        elif self.active_channel is None:
            raise ValueError(
                "No active channel set. Please use either the Chatroom.set_channel() function"
                + " or provide `channel` as a non-null value!"
            )

        if isinstance(content, bytes):
            endpoint = self.endpoints.files
        else:
            endpoint = self.endpoints.messages

        if isinstance(content, str):
            content = content.encode("ascii")

        msg = {
            "username": self.username,
            "channelID": self.active_channel.uid,
            "replyID": reply_id,
            "data": self._encrypt(content),
        }

        sent = self._request(
            "post",
            url=endpoint,
            json=msg,
        )

        if sent is not None:
            sent["data"] = content.decode("ascii")
            self._notify(Event.MSG_SENT, Message.from_dict(sent))


class Teacup:
    """The object to manage all API related actions.

    This class itself doesn't actually do any networking, rather it creates
    objects (`Chatroom`-s) that do all the dirty work.

    Standard flow of using a Teacup:

    ```python3
    from teahaz import Teacup

    cup = Teacup()
    chatroom = cup.login("username", "password", "chatroom-uuid", "url")
    chatroom.send("hello world!")
    ```
    """

    def __init__(self) -> None:
        """Initializes Teacup."""

        self.chatrooms: list[Chatroom] = []
        self._global_listeners: dict[Event, EventCallback] = {}

    def get_threads(self) -> list[str]:
        """Gets names of all chatroom threads."""

        return [chatroom.event_thread.name for chatroom in self.chatrooms]

    def login(self, url: str, chatroom: str, username: str, password: str) -> Chatroom:
        """Creates a logged-in chatroom instance.

        Args:
            url: The server URL:PORT.
            chatroom: The UUID of the chatroom.
            username: Login username for chatroom.
            password: Login password for chatroom.

        Returns:
            A chatroom instance with given user logged in.
        """

        chat = Chatroom(url=url, uid=chatroom)

        for event, callback in self._global_listeners.items():
            chat.subscribe(event, callback)

        chat.login(username, password)
        self.chatrooms.append(chat)

        return chat

    def stop(self) -> None:
        """Stops all chatroom threads."""

        for chatroom in self.chatrooms:
            chatroom.stop()

    def get_chatroom(self, name: str) -> Chatroom | None:
        """Gets first chatroom by matching name.

        Args:
            name: The chatroom display name to search for.
        """

        for chatroom in self.chatrooms:
            if chatroom.name == name:
                return chatroom

        return None

    def create_chatroom(
        self, url: str, name: str, username: str, password: str
    ) -> Chatroom | None:
        """Creates a new chatroom.

        The given user will be the owner of the chatroom.

        Args:
            url: The server URL:PORT.
            name: The display name for the new chatroom.
            username: The login username.
            password: The login password.

        Returns:
            Either the logged-in chatroom, or None if its creation was
            unsuccessful **and** the error raised was captured.
        """

        chat = Chatroom(url=url, name=name)

        # Subscribe chatroom to all global events we are subscribed to
        for event, callback in self._global_listeners.items():
            chat.subscribe(event, callback)

        if chat.create(username, password) is None:
            # Creation failed, but error was captured
            return None

        self.chatrooms.append(chat)
        return chat

    def use_invite(
        self, invite: Invite, username: str, password: str
    ) -> Chatroom | None:
        """Creates a chatroom instance from an invite.

        Args:
            invite: Invite instance.
            username: Username for new chatroom user.
            password: Password for new chatroom user.

        Returns:
            Logged-in chatroom, or None when creation failed but error
            was captured.
        """

        chat = Chatroom(url=invite.url, uid=invite.chatroom_id)
        if chat.create_from_invite(invite, username, password) is None:
            # Creation failed, but error was captured
            return None

        self.chatrooms.append(chat)
        return chat

    def subscribe_all(self, event: Event, callback: EventCallback) -> None:
        """Subscribes callback to event in all (current & future) Chatrooms.

        Args:
            event: The event to subscribe to.
            callback: The callback that shall be called.
        """

        for chatroom in self.chatrooms:
            chatroom.subscribe(event, callback)

        self._global_listeners[event] = callback

    @staticmethod
    def threaded(
        target: Callable[..., Any], callback: Callable[..., Any] | None = None
    ) -> Callable[..., None]:
        """Returns a threaded callable for target.

        Args:
            target: The callable to thread.
            callback: The callable that will be called with return value
                of `target`.

        Returns:
            A lambda function that runs `target` in a thread, passing its
            return value to `callback`.
        """

        def _call_target(*args, **kwargs) -> None:
            """Calls the target."""

            returned = target(*args, **kwargs)
            if callback is not None:
                callback(returned)

        return lambda *args, **kwargs: Thread(
            target=_call_target, args=args, kwargs=kwargs
        ).start()
