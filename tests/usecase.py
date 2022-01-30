from time import sleep
from typing import Any
from requests import Response

from pytermgui import Container, Label, Splitter, boxes, alt_buffer, markup, terminal
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
        markup.alias("code-color", "bold strikethrough 1")
    else:
        markup.alias("code-color", str(colors.get(code)))

    root = Container(width=terminal.width) + Label("[error-title]Error occured!")
    root += {"[error-method]Method:": "[157 bold]" + method.upper()}
    root += {"[error-code]Code:": f"[code-color]{code}"}
    root += {"[error-message]Message:": '[247 italic]"' + response.json() + '"'}

    root += Label("[error-data]request_args[/] = {", parent_align=0)
    for key, item in req_kwargs.items():
        root += Label(
            f"[247 italic]{key}: [157 bold]{item},",
            parent_align=0,
            padding=4,
        )
    root += Label("}", parent_align=0)

    root.center()
    with alt_buffer(cursor=False):
        root.print()
        input()


def setup() -> None:
    """Setup initial styles & values"""

    markup.alias("error-title", "210 italic bold")
    markup.alias("error-code", "72 bold")
    markup.alias("error-data", "72 bold")
    markup.alias("error-method", "72 bold")
    markup.alias("error-message", "72 bold")

    # Prompt.set_char("delimiter", [""] * 2)
    Splitter.set_char("separator", "  ")
    boxes.DOUBLE_TOP.set_chars_of(Container)


def progress_print(content: str) -> None:
    """Print without end newline, with flush & markup parsing"""

    print(f"{markup.parse(content):<35}", flush=True, end="")


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
        lambda msg: rec.append((msg.uid, msg.data)),
    )

    for i in range(count):
        message = "this is message " + str(i)
        sent_msg = chat.send(message)
        sent.append((sent_msg["messageID"], sent_msg["data"]))

    # we need to wait until the next loop iteration
    sleep(chat.interval)

    if sent == rec:
        print("✅")
        return

    for i, (out, inp) in enumerate(zip(sent, rec)):
        if not out == inp:
            print(i, out, inp)


def main() -> None:
    """Main method"""

    setup()

    cup = Teacup()
    cup.subscribe_all(Event.ERROR, handle_error)

    chat = create_chatroom_test(
        cup, "https://teahaz.co.uk", "test-alma", "alma", "1234567890"
    )

    create_channel_test(chat, "__main__")
    # chat.send("hello world!")
    # chat.get_count(1)

    # 100 is the server limit
    message_test(chat, 50)
    cup.stop()


if __name__ == "__main__":
    main()
