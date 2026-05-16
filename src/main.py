from dotenv import load_dotenv

from src.app.agent import ReactSkillAgent
from src.app.memory.session import SessionMemory
from src.app.tracing import format_tracing_status


load_dotenv()


def main() -> None:
    agent = ReactSkillAgent()
    session = SessionMemory()

    print("LangGraph ReAct chatbot. Type 'exit' to quit, '/summary' to inspect memory.")
    print(format_tracing_status())

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        if user_input == "/summary":
            summary = session.memory_summary or "(no summary yet)"
            print(f"Memory: {summary}")
            continue

        if not user_input:
            continue

        result = agent.reply(user_input=user_input, session=session)
        if result.action == "reply" and result.reply_content:
            print(f"Assistant: {result.reply_content}")
        elif result.action == "memorize":
            print("Assistant: [memorized]")
        else:
            print("Assistant: [ignored]")


if __name__ == "__main__":
    main()
