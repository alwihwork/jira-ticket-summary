# Jira Tickets Summary

Daily Slack bot yang ngumpulin semua Jira tickets dari team members di active sprint, format jadi summary yang clean, dan kirim ke Slack channel otomatis.

## Why?
Members suka lupa update status ticket. Script ini bantu lead untuk monitor status terkini ticket-ticket members setiap hari — tanpa perlu buka Jira satu-satu.

## What it Does
1. Connect ke Jira pakai API Token (permanent, gak perlu re-login)
2. Auto-detect active sprint dari board kamu
3. Fetch semua tickets dari configured team members
4. Group tickets by status per member
5. Kirim ke Slack pakai Block Kit (clean, compact, clickable ticket links)
6. Mention semua members biar gak ada yang kelewat

## Slack Output Preview
```
📋 Daily Jira Summary — 01 Apr 2026
Sprint: SME Sprint 50
─────────────────────────────────────
👤 @Alwi
To Do: QML-662, QML-1444
In Progress: QML-1427, QML-1420
Ready To Deploy: QML-1288, QML-1219

👤 @Udin
To Do: QML-1316, QML-1446
In Progress: QML-1428, QML-1330

👤 @Jonathan
...
─────────────────────────────────────
cc: @Alwi @Udin @Jonathan @Chatrin
Please update your ticket status! 🙏
```
> Ticket numbers are clickable links to Jira. Empty statuses are hidden.

## Tech Stack
| Tool | Purpose |
|------|---------|
| Python | Main language |
| UV | Environment & dependency manager |
| Jira REST API v3 | Fetch sprint & tickets (JQL) |
| Slack Block Kit | Rich message formatting |
| crontab | Daily scheduling |

## File Structure
```
jira-tickets-summary/
├── agent.md          # This doc
├── main.py           # Main script (~200 lines)
├── .env.example      # Config template
├── .env              # Your config (gitignored)
├── pyproject.toml    # UV project config
├── requirements.txt  # For servers without UV
└── .gitignore
```

## Quick Start

### 1. Clone & Setup
```bash
git clone <repo-url>
cd jira-tickets-summary
cp .env.example .env
```

### 2. Fill in `.env`
```env
# Jira — get token: https://id.atlassian.com/manage-profile/security/api-tokens
JIRA_BASE_URL=https://your-domain.atlassian.net
JIRA_EMAIL=your-email@company.com
JIRA_API_TOKEN=your-api-token-here
JIRA_BOARD_NAME=Your Board Name

# Team — format: "Jira Display Name:Slack User ID" (comma-separated)
# Slack ID: open profile > ⋮ More > Copy member ID
TEAM_MEMBERS=John Doe:U01ABC123,Jane Smith:U02DEF456

# Slack — create webhook: https://api.slack.com/messaging/webhooks
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY/ZZZ
```

### 3. Install & Run
```bash
# With UV (recommended)
uv sync
uv run python main.py --dry-run    # test print only
uv run python main.py              # send to Slack

# Without UV (prod server)
pip install -r requirements.txt
python main.py --dry-run
python main.py
```

### 4. Discover Statuses (optional)
Jira status names vary per project. Run this to see what statuses exist in your board and auto-generate the mapping:
```bash
uv run python main.py --list-statuses
```
Then copy the suggested `STATUS_MAP` into `main.py`.

### 5. Schedule Daily (crontab)
```bash
crontab -e
# Run every weekday at 9 AM
0 9 * * 1-5 cd /path/to/jira-tickets-summary && uv run python main.py
```

## Commands
| Command | Description |
|---------|-------------|
| `python main.py` | Fetch tickets & send to Slack |
| `python main.py --dry-run` | Print only, no Slack |
| `python main.py --list-statuses` | Show all statuses from your board's active sprint |

## Customization

### Status Mapping
Edit `STATUS_MAP` in `main.py` to match your Jira workflow. Use `--list-statuses` to discover available statuses.

### Status Order
Edit `STATUS_ORDER` to control which statuses appear and in what order.

## Dependencies
Only 2 packages — kept intentionally minimal:
- `requests` — HTTP calls to Jira & Slack
- `python-dotenv` — load `.env` config
