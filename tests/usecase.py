from typing import Any
from requests import Response

from teahaz import Teacup, Event, Message, Chatroom, Channel
from pytermgui import (
    Container,
    Prompt,
    Label,
    boxes,
    alt_buffer,
    define_tag,
    markup_to_ansi,
)


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

    root = Container() + Label(f"[error-title]Error occured!")
    root += Prompt(f"[error-method]Method:", "[157 bold]" + method.upper())
    root += Prompt(f"[error-code]Code:", f"[code-color]{code}")
    root += Prompt(f"[error-message]Message:", '[247 italic]"' + response.json() + '"')

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

    print(markup_to_ansi(content), flush=True, end="")


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
    print("✅\n")

    return chat


def create_channel_test(chat: Chatroom, name: str) -> Channel:
    """Test: create channel"""

    channel = chat.create_channel("main")

    assert channel is not None
    print("✅\n")

    return channel


def main() -> None:
    """Main method"""

    setup()

    cup = Teacup()
    cup.subscribe_all(Event.ERROR, handle_error)

    chat = create_chatroom_test(
        cup, "https://teahaz.co.uk", "test-alma", "alma", "1234567890"
    )

    channel = create_channel_test(chat, "__main__")

    chat.send("hello world!")
    print(chat.get_messages())
    input()

    print(chat)

    input()


if __name__ == "__main__":
    main()
