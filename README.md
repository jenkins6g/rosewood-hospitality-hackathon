# LangGraph ReAct Chatbot Scaffold

Teams-first Python scaffold for a ReAct-style chatbot built with LangGraph and `langchain-openai`, following Garry Tan's thin harness / fat skills pattern.

## What this scaffold demonstrates

- A thin system harness with short, stable prompts
- Fat markdown skill files that hold process and domain logic
- A resolver that selects which skills to inject for each turn
- A three-way `reply | memorize | ignore` action decision in the core graph
- A real tool loop with a minimal thin tool set
- Session memory plus compressed summary memory
- Durable JSONL memory notes for memorized facts
- Local guest profiles and timelines for hotel operations
- A Teams adapter over the same core graph
- A LangGraph state machine instead of a monolithic chat loop

## The five concepts encoded here

1. `Skill files`: reusable markdown workflows in `src/app/skills/*.md`
2. `Thin harness`: short prompts in `src/app/prompts/`
3. `Resolver`: LLM routing over skill metadata in `src/app/resolver/router.py`
4. `Task decomposition`: execution plan stored in graph state and injected into context
5. `Compressed memory`: turn-by-turn summary updates in `src/app/memory/compressor.py`
6. `Teams adapter`: transport-only Teams runtime in `src/adapters/teams.py`

## Project structure

```text
src/
  adapters/
  app/
    config.py
    schemas.py
    state.py
    prompts/
    skills/
    tools/
    resolver/
    memory/
    graph/
    agent.py
  main.py
```

## Local setup

1. Create a virtual environment:
   `python3 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install dependencies:
   `pip install -e .`
4. Copy env vars:
   `cp .env.example .env`
5. Set the OpenAI, Teams, and optional Tavily/Aviationstack credentials in `.env`
6. Start the Teams runtime:
   `python src/teams_main.py`

For CLI debugging:

`python src/main.py`

## LangSmith tracing

To enable LangSmith tracing, set:

- `LANGSMITH_TRACING=true`
- `LANGSMITH_API_KEY`

Optional tracing settings:

- `LANGSMITH_PROJECT` to group traces under a custom project
- `LANGSMITH_WORKSPACE_ID` if your API key can access multiple workspaces
- `LANGCHAIN_BASE_URL` for self-hosted or regional LangSmith deployments
- `LANGCHAIN_CALLBACKS_BACKGROUND=false` for short-lived local debug runs

With tracing enabled, LangChain and LangGraph will trace the model, resolver,
classifier, summarizer, graph execution, and tool calls automatically. Root
trace metadata includes compact adapter context such as source, surface, and
conversation identifiers. Prompt and message content will appear in traces
unless you add anonymization later.

## Default tools

- `calculator`: deterministic arithmetic
- `clock`: current time by timezone
- `docs_lookup`: search local markdown docs and skill files
- `web_search`: current public web research through Tavily
- `flight_status`: live flight arrival/status lookup through Aviationstack

## Default skills

- `generic_research`
- `generic_summary`
- `generic_planning`
- `generic_clarify`
- `teams_conversation_policy`
- `guest_profile_tracking`
- `guest_identity_resolution`
- `flight_arrival_enrichment`
- `property_activity_logging`
- `luxury_concierge_research`

## Guest operations behavior

- Hotel-team messages about guest arrivals, activities, and preferences are usually memorized silently.
- Guest timelines and note-heavy profiles are stored locally under `var/guest_profiles/`.
- The bot uses fuzzy guest matching with recency and current-stay context; if two candidates remain plausible, it asks a follow-up question instead of silently linking the wrong guest.

## Extending the scaffold

- Add a new markdown skill to `src/app/skills/`
- Register another thin tool in `src/app/tools/registry.py`
- Swap models through `OPENAI_MODEL`
- Add more adapters over the same normalized event/result core
