# Teams Echo Bot

Minimal Microsoft Teams echo bot in Python using the current Teams SDK.

## What this project does

- Listens for incoming Teams chat messages
- Replies with a typing indicator
- Echoes the message text back to the user

## Project structure

- `src/main.py`: Teams bot entrypoint and message handlers
- `pyproject.toml`: Python dependencies and scripts
- `.env.example`: Environment variable template for Teams credentials

## Local setup

1. Create a virtual environment:
   `python3 -m venv .venv`
2. Activate it:
   `source .venv/bin/activate`
3. Install dependencies:
   `pip install -e .`
4. Copy env vars:
   `cp .env.example .env`
5. Run the bot:
   `python src/main.py`

The Teams SDK default local port is `3978`. Your bot endpoint should be:

`https://<your-public-url>/api/messages`

## Register the bot in Teams

This repo contains the bot code only. You still need Teams-side app registration and credentials.

With the Teams Developer CLI installed, the flow from the `teams-dev` skill is:

1. Install CLI:
   `npm install -g @microsoft/teams.cli@preview`
2. Log in:
   `teams login`
3. Create a persistent tunnel or use another public HTTPS URL
4. Create the Teams app and write credentials to `.env`:
   `teams app create --name "Echo Bot" --endpoint "https://<your-public-url>/api/messages" --env .env --json`
5. Open the returned `installLink` in your browser to install the bot in Teams

## Notes

- This SDK is not Bot Framework.
- If your tunnel URL changes, update the Teams app endpoint:
  `teams app update <teamsAppId> --endpoint "https://<new-public-url>/api/messages"`
# rosewood-hospitality-hackathon
