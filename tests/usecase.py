from typing import Any
from requests import Response

from teahaz import Teacup, Event, Message, Chatroom
from pytermgui import (
    Container,
    Prompt,
    InputField,
    markup_to_ansi,
    Label,
    alt_buffer,
    define_tag,
    boxes,
    break_line,
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
    boxes.SINGLE.set_chars_of(Container)


def progress_print(content: str) -> None:
    """Print without end newline, with flush & markup parsing"""

    print(markup_to_ansi(content), flush=True, end="")


def main() -> None:
    """Main method"""

    setup()

    cup = Teacup()
    cup.subscribe_all(Event.ERROR, handle_error)

    progress_print("[italic]Creating chatroom... ")
    chat = cup.create_chatroom("https://teahaz.co.uk", "test", "alma", "1234567890")
    print("✅\n")

    print(chat)
    input()

    channel = chat.create_channel("main")
    chat.send("hello world!")
    print(chat.get_messages())
    input()


if __name__ == "__main__":
    main()
