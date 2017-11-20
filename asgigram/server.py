import aiohttp
import asyncio
import logging
from asgiref.server import StatelessServer

from .exceptions import ApiError


logger = logging.getLogger(__name__)


class Server(StatelessServer):
    """
    Telegram bot server. Uses long-polling against the getUpdates endpoint.
    """

    api_timeout = 60
    retry_interval = 30
    retry_statuses = [429, 500, 502, 503, 504]

    def __init__(self, application, token, api_url=None, max_applications=1000):
        super(Server, self).__init__(
            application=application,
            max_applications=max_applications,
        )
        # Parameters
        self.token = token
        self.api_url = api_url or "https://api.telegram.org"
        # Initialisation
        self.update_offset = 0
        self.application_instances = {}

    ### Mainloop and handling

    async def handle(self):
        """
        Main loop. Long-polls and dispatches updates to handlers.
        """
        self.client_session = aiohttp.ClientSession()
        # Confirm our API connection
        me = (await self.call_api("getMe"))["result"]
        logger.info("Logged into Telegram as %s", me.get("username", me["id"]))
        # Do handle loop
        while True:
            updates = await self.call_api(
                "getUpdates",
                offset=self.update_offset + 1,
                timeout=self.api_timeout,
            )
            if not updates.get("ok"):
                raise ApiError("Error with getUpdates: %s" % updates.get("description"))
            for update in updates["result"]:
                await self.handle_update(update)

    async def handle_update(self, update):
        """
        Handles a single update.
        """
        # Store the offset we got up to
        self.update_offset = max(
            update["update_id"],
            self.update_offset,
        )
        # Work out what scope it would need
        scopes = {
            "message": "chat",
            "edited_message": "chat",
            "channel_post": "chat",
            "edited_channel_post": "chat",
        }
        for key, scope in scopes.items():
            if key in update:
                # Extract the basic action out
                action = update[key]
                # We've found the message type
                if scope == "chat":
                    input_queue = self.chat_queue(action["chat"])
                elif scope == "user":
                    input_queue = self.user_queue(action["user"])
                else:
                    raise RuntimeError("Unknown scope %s" % scope)
                # Send the message
                message = dict(action)
                message["type"] = "telegram.%s" % key
                logging.debug("Handling message of type %s", message["type"])
                input_queue.put_nowait(message)
                return
        # If we get here we have no idea what it is.
        raise RuntimeError("Unknown Telegram update type: %s" % update)

    async def application_send(self, scope, message):
        """
        Receives outbound sends from applications and handles them.
        """
        if message["type"] == "telegram.send_message":
            # If there's no chat ID in the message, get it from the scope.
            if "chat_id" not in message:
                if not "chat" in scope:
                    raise ValueError("telegram.message needs a chat_id or to be sent inside a chat scope.")
                message["chat_id"] = scope["chat"]["id"]
            await self.call_api(
                "sendMessage",
                chat_id=message["chat_id"],
                text=message["text"],
                **{
                    k: v
                    for k, v in message.items()
                    if k in ["parse_mode", "reply_to_message_id"]
                }
            )
        else:
            raise RuntimeError("Unknown outbound message type %s" % message["type"])

    ### Application instance management

    def chat_queue(self, chat):
        """
        Creates or returns an application instance for the given chat,
        and returns its input queue.
        """
        return self.get_or_create_application_instance(
            "chat-%s" % chat["id"],
            {
                "type": "telegram",
                "chat": chat,
            },
        )

    def user_queue(self, user):
        """
        Creates or returns an application instance for the given user,
        and returns its input queue.
        """
        return self.get_or_create_application_instance(
            "user-%s" % user["id"],
            {
                "type": "telegram",
                "user": user,
            },
        )

    ### API interaction

    async def call_api(self, method, **params):
        """
        Calls the telegram API.
        """
        url = "{0}/bot{1}/{2}".format(self.api_url, self.token, method)

        response = await self.client_session.post(url, data=params)

        if response.status == 200:
            # Return the decoded JSON response
            return await response.json()

        elif response.status in self.retry_statuses:
            # We need to wait and retry.
            logger.info(
                "API status %d, waiting %ds",
                response.status,
                self.retry_interval,
            )
            await response.release()
            await asyncio.sleep(self.retry_interval)
            return await self.call_api(method, **params)

        else:
            # Genuine error
            if response.headers['content-type'] == 'application/json':
                err_msg = (await response.json(loads=self.json_deserialize))["description"]
            else:
                err_msg = await response.read()
            raise ApiError(err_msg, response=response)
