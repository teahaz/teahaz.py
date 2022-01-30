"""The module containing the abstraction dataclasses used by client.py"""

from __future__ import annotations

from typing import Any
from dataclasses import dataclass

__all__ = [
    "User",
    "Invite",
    "Channel",
    "Message",
    "SystemEvent",
]


@dataclass
class SystemEvent:
    """A class representing a system event."""

    event_type: str

    # Note: This will be changed to event_info
    user_info: str


@dataclass
class Message:
    """A class representing a sent message.

    A message can be one of a couple of types:
    - text: A text message. These will be encrypted in the future.
    - file: A message with a file argument.
    - system: A system event.
    - system-silent: A system event, but one that is more for debug
        purposes. As such, clients should normally not display them.

    The content & type of the data field depends on the message type:
    - text: `str`
    - file: `bytes`
    - system & system-silent: `SystemEvent`
    """

    uid: str
    """The message's UUID."""

    send_time: float
    """Epoch-float time when the message was sent."""

    message_type: str
    """Type of the message. See above for more info."""

    data: str | bytes | SystemEvent
    """The data contained within the message."""

    channel_id: str | None
    """The ID of the channel this message was sent to. This is only
    set when the message type is one of `["text", "file"]`."""

    username: str | None
    """The sender user's username. Only set in the above circumstances."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        """Creates a Message from server-data."""

        data_value: dict[str, Any] | SystemEvent = data["data"]

        if data["type"].startswith("system"):
            assert isinstance(data_value, dict)
            data_value = SystemEvent(data_value["event_type"], data_value["user_info"])

        return cls(
            # All messages
            uid=str(data.get("messageID")),
            send_time=float(data.get("time")),  # type: ignore
            message_type=str(data.get("type")),
            data=data["data"],
            # Only none-system
            channel_id=data.get("channelID"),
            username=data.get("username"),
        )


@dataclass
class Channel:
    """A class representing a Channel inside a Chatroom."""

    uid: str
    """The channel's UUID."""

    name: str
    """The channel's display name."""

    permissions: dict[str, bool]
    """A dictionary of permissions the current user has in this channel. WIP."""

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Channel:
        """Creates a channel from server-data"""

        return cls(
            uid=data["channelID"],
            name=data["name"],
            permissions=data["permissions"],
        )


@dataclass
class User:
    """A dataclass to store user information."""

    uid: str
    username: str
    color: dict[str, int]

    def get_color(self) -> str:
        """Gets user's color as markup tag."""

        return ";".join(str(value) for value in self.color.values())

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> User:
        """Creates user from server-data."""

        return cls(
            uid=data["username"],
            username=data["username"],
            color=data["color"],
        )


@dataclass
class Invite:
    """A dataclass to store invites."""

    url: str
    uid: str
    uses: int
    chatroom_id: str
    expiration_time: float

    @classmethod
    def from_dict(cls, data: dict) -> Invite:
        """Get invite from server-data"""

        return cls(
            url=data["url"],
            uses=data["uses"],
            uid=data["inviteID"],
            chatroom_id=data["chatroomID"],
            expiration_time=data["expiration-time"],
        )
