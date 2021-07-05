from time import sleep
from typing import Any
from requests import Response

from pytermgui import (
    Container,
    Prompt,
    Label,
    boxes,
    alt_buffer,
    define_tag,
    markup_to_ansi,
)
from teahaz import Teacup, Event, Chatroom, Channel


def handle_error(response: Response, method: str, req_kwargs: dict[str, Any]) -> None:
    """Print error"""

    code = response.status_code
    if code == 200:
        raise ValueError(f"Why did this error? {response.text}")

    colors = {
        200: 210,
        400: 210,
        401: 167,
        403: 1,
        500: 69,
    }

    if colors.get(code) is None:
        define_tag("code-color", "bold strikethrough 1")
    else:
        define_tag("code-color", str(colors.get(code)))

    root = Container() + Label("[error-title]Error occured!")
    root += Prompt("[error-method]Method:", "[157 bold]" + method.upper())
    root += Prompt("[error-code]Code:", f"[code-color]{code}")
    root += Prompt("[error-message]Message:", '[247 italic]"' + response.json() + '"')

    root += Label("[error-data]request_args[/] = {", align=Label.ALIGN_LEFT)
    for key, item in req_kwargs.items():
        root += Label(
            f"[247 italic]{key}: [157 bold]{item},",
            align=Label.ALIGN_LEFT,
            padding=4,
        )
    root += Label("}", align=Label.ALIGN_LEFT)

    root.center()
    with alt_buffer(cursor=False):
        root.print()
        input()


def setup() -> None:
    """Setup initial styles & values"""

    define_tag("error-title", "210 italic bold")
    define_tag("error-code", "72 bold")
    define_tag("error-data", "72 bold")
    define_tag("error-method", "72 bold")
    define_tag("error-message", "72 bold")

    Prompt.set_char("delimiter", [""] * 2)
    boxes.DOUBLE_TOP.set_chars_of(Container)


def progress_print(content: str) -> None:
    """Print without end newline, with flush & markup parsing"""

    print(f"{markup_to_ansi(content):<35}", flush=True, end="")


def create_chatroom_test(
    cup: Teacup, url: str, name: str, username: str, password: str
) -> Chatroom:
    """Test: create chatroom"""

    progress_print("[italic]Creating chatroom... ")
    chat = cup.create_chatroom(
        url,
        name,
        username,
        password,
    )

    assert chat is not None
    print("✅")

    return chat


def create_channel_test(chat: Chatroom, name: str) -> Channel:
    """Test: create channel"""

    progress_print("[italic]Creating channel... ")
    channel = chat.create_channel(name)

    assert channel is not None
    print("✅")

    return channel


def message_test(chat: Chatroom, count: int = 100) -> None:
    """Test: send count messages, check if sent & receieved are the same

    Note: This usecase is not realistic at all, it's just to test the
    chatroom loop's functionality."""

    progress_print(f"[italic]Sending {count} messages... ")
    sent: list[str] = []
    rec: list[str] = []

    chat.subscribe(
        Event.MSG_NEW,
        lambda msg: rec.append(msg.uid),
    )

    for i in range(count):
        message = "this is message " + str(i)
        sent.append(chat.send(message)["messageID"])

    # we need to wait until the next loop iteration
    sleep(chat.interval)

    assert sent == rec
    print("✅")


def main() -> None:
    """Main method"""

    setup()

    cup = Teacup()
    cup.subscribe_all(Event.ERROR, handle_error)

    chat = create_chatroom_test(
        cup, "http://localhost:13337", "test-alma", "alma", "1234567890"
    )

    create_channel_test(chat, "__main__")
    chat.send("hello world!")

    # 100 is the server limit
    message_test(chat, 50)
    cup.stop()


if __name__ == "__main__":
    main()
