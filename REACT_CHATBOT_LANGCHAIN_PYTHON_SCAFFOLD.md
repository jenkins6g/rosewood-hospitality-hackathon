# ReAct Chatbot Scaffold in Python with LangChain

This guide is a simple scaffold for creating a ReAct-style chatbot in another Python repo using LangChain.

It intentionally excludes tool integrations. The goal is to give you a clean structure you can port, then wire to your own app, API routes, storage, and runtime later.

## What You Are Building

A basic ReAct chatbot usually has these parts:

1. A system prompt that defines the assistant's behavior.
2. A user input loop.
3. A reasoning pattern where the model thinks step by step before answering.
4. Optional conversation memory.
5. A thin application layer so you can swap UI, storage, or model providers later.

For a no-tools scaffold, the chatbot can still follow a ReAct-style format internally:

- Understand the user request.
- Reason through the task.
- Produce a final answer.

## Suggested Project Structure

```text
your_project/
  app/
    __init__.py
    config.py
    prompts.py
    chains.py
    chatbot.py
    schemas.py
  main.py
  requirements.txt
  .env.example
```

## Suggested Responsibilities

### `app/config.py`

Store environment-driven configuration:

- model name
- API key loading
- temperature
- max tokens

### `app/prompts.py`

Keep prompt templates separate from chain logic.

Recommended prompts:

- system prompt
- chat prompt template
- response format instructions

### `app/schemas.py`

Keep simple request and response objects here.

Example:

- `ChatRequest`
- `ChatResponse`
- `Message`

### `app/chains.py`

Create the LangChain model and prompt chain here.

This file should:

- initialize the chat model
- combine prompt + model
- expose one function that returns a runnable chain

### `app/chatbot.py`

This is the app-facing orchestration layer.

It should:

- accept user input
- pass history + current message into the chain
- return the assistant response

### `main.py`

Temporary local entrypoint for CLI testing before you embed it into another repo.

## ReAct Prompt Scaffold

Since you do not want tools in this version, keep the prompt focused on reasoning and answer quality instead of action execution.

Example system prompt:

```text
You are a helpful assistant that uses a ReAct-style reasoning process.

Follow this approach internally:
1. Understand the user's goal.
2. Break the problem into clear steps.
3. Reason carefully before answering.
4. Provide a concise final answer.

Do not mention hidden chain-of-thought.
Do not expose internal reasoning unless the user explicitly asks for a brief explanation.
Keep answers accurate, direct, and useful.
```

If you want visible reasoning structure without revealing chain-of-thought, use a safer output shape like:

```text
When useful, format responses as:

Goal: <short interpretation of the user's request>
Plan: <brief high-level plan>
Answer: <final response>
```

## Minimal LangChain Scaffold

### `app/config.py`

```python
import os
from dataclasses import dataclass


@dataclass
class Settings:
    model_name: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    temperature: float = float(os.getenv("MODEL_TEMPERATURE", "0.2"))


settings = Settings()
```

### `app/prompts.py`

```python
SYSTEM_PROMPT = """
You are a helpful assistant that uses a ReAct-style reasoning process.

Follow this approach internally:
1. Understand the user's goal.
2. Break the problem into clear steps.
3. Reason carefully before answering.
4. Provide a concise final answer.

Do not expose hidden chain-of-thought.
Keep answers accurate, direct, and useful.
""".strip()
```

### `app/schemas.py`

```python
from dataclasses import dataclass, field


@dataclass
class Message:
    role: str
    content: str


@dataclass
class ChatRequest:
    user_input: str
    history: list[Message] = field(default_factory=list)


@dataclass
class ChatResponse:
    content: str
```

### `app/chains.py`

```python
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI

from app.config import settings
from app.prompts import SYSTEM_PROMPT


def build_chat_chain():
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{user_input}"),
        ]
    )

    model = ChatOpenAI(
        model=settings.model_name,
        temperature=settings.temperature,
    )

    return prompt | model
```

### `app/chatbot.py`

```python
from langchain_core.messages import AIMessage, HumanMessage

from app.chains import build_chat_chain
from app.schemas import ChatRequest, ChatResponse


class ReactChatbot:
    def __init__(self):
        self.chain = build_chat_chain()

    def reply(self, request: ChatRequest) -> ChatResponse:
        history = []

        for msg in request.history:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            elif msg.role == "assistant":
                history.append(AIMessage(content=msg.content))

        response = self.chain.invoke(
            {
                "history": history,
                "user_input": request.user_input,
            }
        )

        return ChatResponse(content=response.content)
```

### `main.py`

```python
from app.chatbot import ReactChatbot
from app.schemas import ChatRequest, Message


def main():
    bot = ReactChatbot()
    history: list[Message] = []

    print("ReAct chatbot. Type 'exit' to quit.")

    while True:
        user_input = input("You: ").strip()

        if user_input.lower() in {"exit", "quit"}:
            break

        request = ChatRequest(user_input=user_input, history=history)
        response = bot.reply(request)

        print(f"Bot: {response.content}")

        history.append(Message(role="user", content=user_input))
        history.append(Message(role="assistant", content=response.content))


if __name__ == "__main__":
    main()
```

## Requirements Scaffold

Example `requirements.txt`:

```text
langchain
langchain-openai
python-dotenv
```

## Memory Options

For a portable version, keep memory simple at first.

You can start with:

- in-memory chat history stored in a list

Later you can swap this for:

- Redis-backed chat history
- database-backed sessions
- per-user conversation threads

Keep memory outside the core chain where possible so the chatbot logic stays portable.

## Porting Notes

When moving this into another repo, usually only these parts need to change:

1. `main.py` becomes a web route, job handler, or service method.
2. `history` comes from your app's session or database layer.
3. `config.py` reads from that repo's config system.
4. `ChatOpenAI` can be replaced with another supported chat model if needed.

## Good Defaults

Use these defaults unless your target app already has stronger conventions:

- low temperature
- short, direct responses
- prompt templates isolated from business logic
- request and response schemas separated from chain construction
- one orchestration class that the rest of the app calls

## Next Step After Porting

Once this scaffold is in the new repo, the usual next additions are:

1. web API wrapper
2. persistent chat history
3. authentication or per-user session handling
4. streaming responses
5. structured output for downstream UI rendering

This scaffold keeps those concerns out on purpose so the core chatbot is easy to transplant.
