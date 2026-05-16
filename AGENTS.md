# Thin Harness, Fat Skills

This repository uses a thin-harness, fat-skills architecture for all agent work.

## Non-Negotiable Rules

- Keep harness prompts short, generic, and stable.
- Put domain or workflow detail in markdown skill files under `src/app/skills/`.
- Route context through the resolver before the main agent node whenever behavior depends on task type.
- Prefer a small explicit tool registry over broad multi-purpose tools.
- Keep memory compressed and reusable; do not replay long raw histories when a summary will do.

## Prompt Boundaries

- Files in `src/app/prompts/` define the thin harness only.
- Do not embed domain-specific procedures, long examples, or large policy blocks in harness prompts.
- If new behavior requires detailed instructions, create or extend a skill file instead.

## Skill Boundaries

- Each skill should define when it is used, the inputs it expects, and the steps it wants followed.
- Skills are markdown-first and should remain readable and concise.
- Add new reusable workflows as new skill files instead of branching the system prompt.

## Resolver Boundaries

- Multi-domain or multi-workflow behavior must flow through the resolver.
- Do not bypass the resolver by hardcoding task routing in the main harness prompt.
- If deterministic prefiltering is needed later, keep the final selection logic compatible with the resolver model.

## Tooling Boundaries

- New tools must be narrow, deterministic, and easy to describe in one sentence.
- Prefer local tools that return compact outputs.
- Avoid “god tools” that combine search, planning, and side effects behind one interface.

## Memory Boundaries

- Keep session memory as short history plus compressed summary.
- Summaries should preserve preferences, constraints, and unresolved tasks.
- Do not grow the harness prompt to compensate for missing memory design.

## Validation Expectations

- Update architecture tests when adding new prompt or skill conventions.
- If you add a prompt, skill, or tool surface that changes this pattern, update `tests/test_architecture.py`.
