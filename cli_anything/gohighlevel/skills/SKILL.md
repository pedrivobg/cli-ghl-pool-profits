---
name: "cli-anything-gohighlevel"
description: "CLI interface for GoHighLevel CRM/Marketing API — contacts, opportunities, calendars, workflows, conversations, emails, payments, forms, social media, locations"
triggers:
  - gohighlevel
  - ghl cli
  - ghl contacts
  - ghl workflows
  - ghl calendars
---

# cli-anything-gohighlevel

CLI interface for the GoHighLevel (GHL) CRM and Marketing API. Manage contacts, pipeline opportunities, calendars, workflows, conversations, emails, payments, forms, social media posts, and locations from the command line or interactive REPL.

## Prerequisites

- Python 3.10+
- `GHL_API_KEY` environment variable set with your GHL API bearer token
- `GHL_LOCATION_ID` environment variable (sub-account ID; for agency-wide work use the scripts in `scripts/` instead)

## Installation

```bash
cd ~/Documents/Tech\ &\ Dev/highlevel-api-docs/agent-harness
pip install -e .
```

## Usage

### CLI Mode (one-shot commands)
```bash
ghl contacts list --json
ghl contacts get <contact_id>
ghl contacts create --email user@example.com --first-name John --last-name Doe
ghl opportunities list --status open
ghl calendars list
ghl workflows list
ghl conversations list --status unread
ghl payments transactions
ghl forms list
ghl social posts
ghl locations get
```

### REPL Mode (interactive)
```bash
ghl
# or
cli-anything-gohighlevel
```

### Global Options
- `--json` — Output as machine-readable JSON (recommended for agents)
- `--location-id <ID>` — Override GHL_LOCATION_ID for this command
- `--version` — Show CLI version
- `--help` — Show help

## Command Groups

| Group | Description | Key Commands |
|-------|-------------|--------------|
| `contacts` | Contact management | list, get, create, update, delete, search, add-tag, remove-tag |
| `opportunities` | Pipeline deals | list, get, create, update, delete, pipelines |
| `calendars` | Scheduling | list, get, slots, appointments, book, groups |
| `workflows` | Automation workflows | list |
| `conversations` | Messaging (SMS, email, chat) | list, get, messages, send |
| `emails` | Email campaigns/templates | list-campaigns |
| `payments` | Financial operations | transactions, orders, invoices, create-invoice |
| `forms` | Form management | list, submissions |
| `social` | Social media posting | accounts, posts, create-post |
| `locations` | Sub-account management | get, search, tags, custom-fields, custom-values |

## Agent Usage Notes

- Always use `--json` flag for programmatic consumption
- Contact search uses `contacts search <query>` for name-based search
- Workflow enrollment is done via `contacts` group (not workflows): the GHL API triggers workflows through contact endpoints
- Social media posting requires OAuth-connected accounts
- All endpoints require valid `GHL_API_KEY` bearer token
- API base URL: `https://services.leadconnectorhq.com`
- API version header: `2021-07-28`

## Examples

```bash
# List contacts as JSON
ghl --json contacts list --limit 50

# Create a contact with tags
ghl contacts create --email lead@company.com --first-name Jane --last-name Smith --tag "hot-lead" --tag "webinar"

# Search contacts
ghl contacts search "john"

# List pipeline opportunities
ghl --json opportunities list --status open

# Get available calendar slots
ghl calendars slots <calendar_id> --start 2026-03-25 --end 2026-03-30

# Send SMS in conversation
ghl conversations send <conversation_id> --type SMS --message "Thanks for your interest!"

# List transactions
ghl --json payments transactions --limit 50

# Create social post
ghl social create-post --account-id <id> --text "New blog post!" --schedule "2026-03-26T10:00:00Z"
```
