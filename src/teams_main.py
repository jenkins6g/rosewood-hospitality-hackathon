import asyncio

from dotenv import load_dotenv
from microsoft_teams.api import MessageActivity
from microsoft_teams.apps import ActivityContext, App

from src.adapters.teams import TeamsAdapter
from src.app.agent import ReactSkillAgent
from src.app.config import settings
from src.app.memory.session_store import SessionStore
from src.app.tracing import format_tracing_status


load_dotenv()

teams_app = App()
adapter: TeamsAdapter | None = None


def get_adapter() -> TeamsAdapter:
    global adapter
    if adapter is None:
        adapter = TeamsAdapter(agent=ReactSkillAgent(), sessions=SessionStore())
    return adapter


@teams_app.on_message
async def handle_teams_message(ctx: ActivityContext[MessageActivity]) -> None:
    await get_adapter().handle_message(ctx)


def main() -> None:
    print(format_tracing_status())
    asyncio.run(teams_app.start(settings.teams_port))


if __name__ == "__main__":
    main()
