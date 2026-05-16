import asyncio
import logging
import random
import re
import traceback

from microsoft_teams.api import MessageActivity, MessageActivityInput
from microsoft_teams.apps import ActivityContext, App

app = App()
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


@app.on_message_pattern(re.compile(r"hello|hi|greetings", re.IGNORECASE))
async def handle_greeting(ctx: ActivityContext[MessageActivity]) -> None:
    await ctx.send("Hello! Send me any message and I will echo it back.")


def _conversation_type(ctx: ActivityContext[MessageActivity]) -> str:
    conversation = getattr(ctx.activity, "conversation", None)
    return (getattr(conversation, "conversation_type", "") or "").lower()


def _bot_is_mentioned(ctx: ActivityContext[MessageActivity]) -> bool:
    text = (ctx.activity.text or "").lower()
    recipient = getattr(ctx.activity, "recipient", None)
    bot_name = (getattr(recipient, "name", "") or "").lower()
    bot_id = (getattr(recipient, "id", "") or "").lower()

    return any(
        needle
        for needle in (bot_name, bot_id)
        if needle and needle in text
    )


def _account_name(account: object) -> str:
    return (
        getattr(account, "display_name", None)
        or getattr(account, "name", None)
        or getattr(account, "given_name", None)
        or getattr(account, "id", "unknown")
    )


def _account_id(account: object) -> str:
    return str(getattr(account, "id", "") or "")


async def _pick_member(ctx: ActivityContext[MessageActivity]) -> object | None:
    members = await ctx.api.conversations.members(
        ctx.activity.conversation.id
    ).get_all()
    recipient = getattr(ctx.activity, "recipient", None)
    bot_id = _account_id(recipient).lower()

    human_members = [
        member for member in members if _account_id(member).lower() != bot_id
    ]

    log.info("Conversation members: %s", [_account_name(member) for member in human_members])

    if not human_members:
        return None

    if len(human_members) == 1:
        return human_members[0]

    return random.choice(human_members)


@app.on_message
async def handle_message(ctx: ActivityContext[MessageActivity]) -> None:
    try:
        text = (ctx.activity.text or "").strip()
        convo_type = _conversation_type(ctx)
        mentioned = _bot_is_mentioned(ctx)

        log.info(
            "Received message type=%s mentioned=%s text=%r",
            convo_type or "unknown",
            mentioned,
            text,
        )

        if convo_type == "personal" or mentioned:
            chosen_member = await _pick_member(ctx)

            if chosen_member is None:
                await ctx.send(f"You said: {text}")
                return

            message = (
                MessageActivityInput(text=f"You said: {text}")
                .add_mention(account=chosen_member)
            )
            await ctx.send(message)
        else:
            log.info("Ignoring non-mention message in non-personal conversation")
    except Exception:
        log.error("Message handler failed:\n%s", traceback.format_exc())
        raise


def main() -> None:
    asyncio.run(app.start())


if __name__ == "__main__":
    main()
