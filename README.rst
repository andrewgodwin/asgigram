asgigram
========

An ASGI server for Telegram bots. Connects to the Telegram API using the
long-polling ``getUpdates`` endpoint, and dispatches incoming updates
into an ASGI application following the ASGI protocol specification below.

It is currently very much in beta, and should not be used for production code.


Installation
------------

::

    pip install asgigram


Usage
-----

::

    asgigram "01234567:your_token_here" your_project.asgi:application


ASGI Protocol Specification
---------------------------

The Telegram API is exposed with each chat (including private messages from
users) as a separate connection scope, and with different event types for the
various kinds of update.


Connection Scope
''''''''''''''''

Connection are "scoped" by the chat identifier, which means in practice you
will have a different scope per chat or user. Because the Telegram API is
stateless, scopes do not last the lifetime of the user or chat's interaction
with the bot.

Instead, the scope and application instance will be made when the user
first interacts with the bot after process start, and will be lost either when
the user has been inactive for some time and it is garbage-collected or when
the current process ends.

If you want to manage long-lasting, per-user state, it's recommended you use
a database or some kind of session store.

The scope contains:

* ``type``: ``telegram``

* ``chat``: Telegram Chat object, containing at minimum an ``id`` key with an
            integer chat ID.

* ``user``: Telegram User object, containing at minimum an ``id`` key with an
            integer user ID.

Exactly one of ``chat`` or ``user`` will be present. Event types below include
which type of scope they will occur in.


Message (Incoming)
''''''''''''''''''

An incoming message in a chat (channel, group, supergroup, private message).

Keys:

* ``type``: ``telegram.message``

* Remaining keys match the `Telegram Message object <https://core.telegram.org/bots/api#message>`_.


Message (Outgoing)
''''''''''''''''''

An outgoing message to a chat.

Keys:

* ``type``: ``telegram.send_message``

* ``text``: Unicode string of the text to send.

* ``chat_id``: Optional integer chat ID to send to or unicode string chat name
  (in format ``@chatname``). If not provided, will default to the
  current chat scope. If you are in a user scope, you must provide
  this.

* ``parse_mode``: Optional Unicode string with value ``Markdown`` or ``HTML``
  if the value of ``text`` is to be treated as a markup language.

* ``reply_to_message_id``: Optional integer Telegram message ID that this is a
  reply to.
