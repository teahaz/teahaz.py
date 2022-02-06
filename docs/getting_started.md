# Getting started

The goal of this library is to provide a simple to use interface for the Teahaz
API. As such, getting started should be relatively easy.

## Library Architecture

Most interactions with `teahaz.py` are done through the `teahaz.clients.Chatroom`
object. This is the object that represents each chatroom, allows assigning callbacks
to events and sending messages, to name a few things.

Acquiring and managing chatrooms is handled by the `teahaz.clients.Teacup` class.
This class _should_ usually be the entrypoint into the library. It has methods, such
as `teahaz.clients.Teacup.login` and `teahaz.clients.Teacup.create_chatroom` that
will provide you with logged in chatroom instances. It also has a helper method, 
`teahaz.clients.Teacup.threaded`, which returns a threaded version of the given
callable, preserving the original signature.

This might be a good point to mention that this libary uses threads over async for
concurrency.


## Gaining access to a chatroom

Before you can do anything fancy, you need access to a chatroom. Servers are
organized into isolated containers called chatrooms, which are then further
segmented into channels. You can learn more about this over at the [server-docs](
https://github.com/teahaz/teahaz-server/).

In order to interact in a chatroom, one needs to somehow get in. There is a couple
of ways to do this.

### Creating your own chatroom

The most nuclear option is to create your own chatroom on the server. You will likely
be limited to doing this on your own server instance, or one where the owner trusts
you.

To do this, take a look at the following code snippet:

```python3
from teahaz import Teacup

cup = Teacup()
chat = cup.create_chatroom(
    "https://example.com", 
    "My New Chatroom", 
    "username",
    "password",
)
```

This will give you a `teahaz.client.Chatroom` instance logged into the new chatroom.
This new chatroom will have the given user registered, as well as made the chatroom
"owner".

### Using an invite

The much easier (and more common) way to get into a chatroom is by using an invite. This
allows you to "register" a new account to the chatroom. Creating invites is once again
permission limited, and invites have both an expiration date and maximum use count.

To create an invite, you can use the `dataclasses.asdict` method on a `teahaz.dataclasses.Invite`:

```python3
import json
import time
from dataclasses import asdict

chat = ... # Your already defined chatroom

# Create an invite expiring in 1 hour (60 seconds * 60), with 10 uses
invite = chat.create_invite(uses=10, timeout=time.time() + 3600)

with open("chat.inv", "w") as invfile:
    invfile.write(json.load(asdict(invite)))
```

Once you have your invite as a file, you need to load and use it:

```python3
import json
from teahaz import Teacup, Invite

cup = Teacup()

with open("chat.inv", "r") as invfile:
    invite = Invite.from_data(json.load(invfile))

chat = cup.use_invite(invite, "username", "password")
```

Note that **from_data** is a standard method for all of `teahaz.dataclasses`. You rarely
need to construct them yourself, but the method is used internally as well.


### Logging in

Once either of the above steps have been completed prior, you can also simply log into the
chatroom to get a reference to it:

```python3
from teahaz import Teacup

chat = cup.login("https://example.com", "username", "password")
```

**All below examples assume any of these sections of code have been executed.** Thus, we
already have both `cup` and `chat` defined.

## Using a Chatroom object

As mentioned above, most interaction with the API is done inside a Chatroom instance.

### The event system

Chatrooms can listen to certain happenings on the server. These are listed and documented
inside the `teahaz.client.Event` enum. The signature of each callback is defined there as
well.

Note that the below examples use lambda functions for brevity: they should generally be
avoided in "real" code.

You can subscribe a specific chatroom to an event using the `teahaz.client.Chatroom.subscribe`
method:

```python3
from teahaz import Event

chat.subscribe(Event.MSG_NEW, lambda message: print("New message!", message))
```

If you want all current **and** future chatrooms to handle certain events in a uniform way,
you can use `teahaz.client.Teacup.subscribe_all`. This method takes the same argument, but
calls the subscribe method on each current & future chatroom.

This is useful to implement universal error handling:

```python3
from teahaz import Event
cup.subscribe_all(Event.ERROR, lambda res, meth, args: print("Error!", res, meth, args))
```

### Sending messages

Sending messages is as easy as calling `teahaz.clients.Chatroom.send` with a file or string
argument. If the `channel` parameter is not provided `Chatroom.active_channel` is used to
send the message.  When it _is_ provided, `active_channel` is updated to the given
`teahaz.clients.Channel` instance, and the message is sent using it instead.

```python3
chat.subscribe(Event.MSG_NEW, lambda msg: print(f"{chat.channel.name}: {msg.data}"))
secondary = chat.create_channel("secondary")

# Prints: "default: First message"
chat.send("First message")

# Prints: "secondary: Second message"
chat.send("Second message", channel=secondary)

# Prints: "secondary: Third message"
chat.send("Third message")
```


## Implementing a simple bot

The teacup class was partially purpose built to be easy to use for bots. As such, for most
purposes you can simpy subclass it and add your own behaviour.

Here is a fully functioning implementation:

```python3
from teahaz import Teacup, Event, Message

class TeahazBot(Teacup):
    
    def __init__(self) -> None:
        super().__init__()

        # We thread the message callback to allow parallel execution
        self.subscribe_all(Event.MSG_NEW, self.threaded(self.on_message))

    def find_chatroom(self, message: Message) -> Chatroom:
        for chatroom in self.chatroom:
            if chatroom.uid == message.chatroom_id:
                return chatroom

        raise ValueError(f"Could not find chatroom belonging to {message}")

    def on_message(self, message: Message) -> None:
        chatroom = self.find_chatroom(message)

        # Don't trigger on messages sent by the bot
        if chatroom.username == message.username:
            return

        chatroom.send("This is my response!", reply_id=message.uid)
```

Once the bot has been constructed, you can call `login`, `create_chatroom` and all other
methods on it the same way a normal Teacup would allow you to.
