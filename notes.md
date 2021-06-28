Example usage of the teahaz.py interface:
-----------------------------------------
```python {{{1
>>> from teahaz import Teacup, Event, Message, Chatroom

>>> cup = Teacup()
empty Teacup()

>>> chat = cup.login("alma", "1234567890", chatroom="thisisachatroomid")
Chatroom(uid="thisisachatroomid")

>>> def handler(message: Message, chatroom: Chatroom):
...     print("message received!")
...     print(f"{message.time = }")
...     print(f"{message.sender = }")
...     print(f"{message.sender_uid = }\n")
...     print(f"{message.type = }")
...     print(f"{message.content = }")
>>> chat.subscribe(Event.MSG_NEW, handler)

>>> chat.send("hello world!")
Message(sender="alma", content="hello world!" ...)

>>> ...
'message received!'
'message.time = 1648585349.67'
'message.sender = alma'
'message.sender_uid = <idkhowuidswork>'

'message.type = text'
'message.content = hello world!'
#  OR
'message.type = file'
'message.content = B2u8rhfZHFL...'

>>> def britney(message: Message, chatroom: Chatroom)
...     if message.type == "file":
...         return
... 
...     if "britney" in message.content:
...         chatroom.send("wassup")

>>> cup.subscribe_all("message", britney)
'Now britney is run on every message from any chatroom'

>>> cup.chatrooms
[Chatroom(uid="thisisachatroomid"), Chatroom(uid="thisisanother")]

>>> chat = cup.get_chatroom("thisisanother")
Chatroom(uid="thisisanother")
```
<!-- }}} -->
