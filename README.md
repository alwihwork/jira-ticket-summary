# Jira Tickets Summary

Daily Slack bot that collects Jira tickets from team members in the active sprint, formats them into a clean summary, and sends it to a Slack channel.

## Features
- Connects to Jira via API Token.
- Auto-detects the active sprint.
- Fetches tickets for specific team members.
- Groups tickets by status per member.
- Sends a rich Slack message using Block Kit.

## Setup
1. Copy `.env.example` to `.env`.
2. Fill in your Jira and Slack credentials.
3. Run `uv sync` to install dependencies.
4. Run `uv run python main.py` to send the summary.
