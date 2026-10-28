import os
import json
import requests
import argparse
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# --- Configs ---
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_BOARD_NAME = os.getenv("JIRA_BOARD_NAME")
TEAM_MEMBERS = os.getenv("TEAM_MEMBERS", "")  # Display Name:Slack ID
FEMALE_MEMBERS = os.getenv("FEMALE_MEMBERS", "")  # Display Name,Display Name
SLACK_CRED = os.getenv("SLACK_CRED")
SLACK_CHANNEL = os.getenv("SLACK_CHANNEL")

# Auth
AUTH = (JIRA_EMAIL, JIRA_API_TOKEN)
HEADERS = {"Accept": "application/json", "Content-Type": "application/json"}

def fetch_json(url, params=None):
    response = requests.get(url, params=params, auth=AUTH, headers=HEADERS)
    response.raise_for_status()
    return response.json()

def get_board_id(name):
    url = f"{JIRA_BASE_URL}/rest/agile/1.0/board"
    start_at = 0
    while True:
        data = fetch_json(url, params={"name": name, "startAt": start_at})
        for board in data.get("values", []):
            if board["name"] == name:
                return board["id"]
        if data.get("isLast", True):
            break
        start_at += data["maxResults"]
    raise Exception(f"Board '{name}' not found.")

def get_active_sprint_id(board_id):
    url = f"{JIRA_BASE_URL}/rest/agile/1.0/board/{board_id}/sprint"
    data = fetch_json(url, params={"state": "active"})
    sprints = data.get("values", [])
    if not sprints:
        raise Exception("No active sprint found.")
    return sprints[0]["id"], sprints[0]["name"]

def fetch_sprint_issues(board_id, sprint_id):
    url = f"{JIRA_BASE_URL}/rest/agile/1.0/board/{board_id}/sprint/{sprint_id}/issue"
    issues = []
    start_at = 0
    while True:
        data = fetch_json(url, params={"startAt": start_at, "maxResults": 100})
        issues.extend(data.get("issues", []))
        if start_at + data["maxResults"] >= data["total"]:
            break
        start_at += data["maxResults"]
    return issues

def parse_team_members(raw_string):
    mapping = {}
    if not raw_string:
        return mapping
    for pair in raw_string.split(","):
        if ":" in pair:
            jira_name, slack_id = pair.split(":", 1)
            mapping[jira_name.strip()] = slack_id.strip()
    return mapping

def parse_female_members(raw_string):
    return {name.strip() for name in raw_string.split(",") if name.strip()}

def get_member_emoji(jira_name):
    """Return emoji based on team member"""
    female_members = parse_female_members(FEMALE_MEMBERS)
    if jira_name in female_members:
        return ":female-technologist::skin-tone-2:"
    return ":male-technologist::skin-tone-2:"

def sort_status_key(status):
    """Custom sort order for statuses"""
    order = {"To Do": 1, "In Progress": 2, "Done": 3}
    return order.get(status, 999)  # Unknown statuses go to the end

def generate_slack_summary(sprint_name, issues, team_mapping):
    # Group issues by assignee and then status
    grouped = {}
    
    # Initialize for team members to ensure they appear even with no issues
    for jira_name in team_mapping.keys():
        grouped[jira_name] = {}

    for issue in issues:
        assignee = issue["fields"].get("assignee")
        if not assignee:
            continue
        
        jira_name = assignee["displayName"]
        # Only track members in our list
        if jira_name not in team_mapping:
            continue
            
        status = issue["fields"]["status"]["name"]
        key = issue["key"]
        
        if status not in grouped[jira_name]:
            grouped[jira_name][status] = []
        grouped[jira_name][status].append(key)

    # Build Slack Blocks
    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"📋 Daily Jira Summary — {datetime.now().strftime('%d %b %Y')}",
                "emoji": True
            }
        },
        {
            "type": "context",
            "elements": [{"type": "mrkdwn", "text": f"_*Sprint:* {sprint_name}_"}]
        },
        {"type": "divider"}
    ]

    for jira_name, slack_id in team_mapping.items():
        user_issues = grouped.get(jira_name, {})
        if not user_issues:
            # Maybe skip if no issues? Or show "No Active Tickets"
            continue
            
        sections = []
        # Sort statuses by custom order: To Do, In Progress, Done
        for status, keys in sorted(user_issues.items(), key=lambda x: sort_status_key(x[0])):
            link_list = ", ".join([f"<{JIRA_BASE_URL}/browse/{k}|{k}>" for k in keys])
            sections.append(f"*{status}:* {link_list}")
        
        content = "\n".join(sections) if sections else "_No active tickets_"
        emoji = get_member_emoji(jira_name)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *<@{slack_id}>*\n{content}"
            }
        })

    blocks.append({"type": "divider"})
    
    mentions = " ".join([f"<@{sid}>" for sid in team_mapping.values()])
    blocks.append({
        "type": "context",
        "elements": [{
            "type": "mrkdwn",
            "text": f"_cc: {mentions} – Please update your ticket status! 🙏_"
        }]
    })

    return {"blocks": blocks}

def list_statuses(issues):
    statuses = sorted(list(set(i["fields"]["status"]["name"] for i in issues)))
    print("\n--- Detected Statuses in Current Sprint ---")
    for s in statuses:
        print(f"- {s}")
    print("-------------------------------------------\n")

def list_assignees(issues):
    assignees = {}
    for issue in issues:
        assignee = issue["fields"].get("assignee")
        if assignee:
            display_name = assignee["displayName"]
            if display_name not in assignees:
                assignees[display_name] = []
            assignees[display_name].append(issue["key"])
    
    print("\n--- Assignees in Current Sprint ---")
    print("Copy these exact names to your .env TEAM_MEMBERS:")
    print()
    for name in sorted(assignees.keys()):
        ticket_count = len(assignees[name])
        print(f"  {name} ({ticket_count} ticket{'s' if ticket_count != 1 else ''})")
    print("\nExample format for .env:")
    print('TEAM_MEMBERS="John Doe:U01ABC123,Jane Smith:U02DEF456"')
    print("-------------------------------------------\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print summary instead of sending to Slack")
    parser.add_argument("--list-statuses", action="store_true", help="List all unique statuses found in the sprint")
    parser.add_argument("--list-assignees", action="store_true", help="List all assignees with their exact Jira display names")
    args = parser.parse_args()

    if not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_BOARD_NAME]):
        print("Error: Missing Jira configuration in .env")
        return

    try:
        board_id = get_board_id(JIRA_BOARD_NAME)
        sprint_id, sprint_name = get_active_sprint_id(board_id)
        issues = fetch_sprint_issues(board_id, sprint_id)
        
        if args.list_statuses:
            list_statuses(issues)
            return
        
        if args.list_assignees:
            list_assignees(issues)
            return

        team_mapping = parse_team_members(TEAM_MEMBERS)
        if not team_mapping:
            print("Error: TEAM_MEMBERS not set or empty in .env")
            return
            
        slack_payload = generate_slack_summary(sprint_name, issues, team_mapping)

        if args.dry_run:
            print(json.dumps(slack_payload, indent=2))
        else:
            if not SLACK_CRED or not SLACK_CHANNEL:
                print("Error: SLACK_CRED or SLACK_CHANNEL not set in .env")
                return
            slack_payload["channel"] = SLACK_CHANNEL
            resp = requests.post(
                "https://slack.com/api/chat.postMessage",
                json=slack_payload,
                headers={
                    "Authorization": f"Bearer {SLACK_CRED}",
                    "Content-Type": "application/json"
                }
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                print(f"Error: Slack API error: {data.get('error')}")
            else:
                print("Successfully sent to Slack!")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

