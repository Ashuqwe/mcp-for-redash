# MCP for Redash

Connect Codex, Claude Code, Cursor, and other MCP-compatible AI tools to Redash.

This project is a local MCP server written in Python. It gives your AI assistant a safe, structured way to list Redash assets, run queries, inspect dashboards, manage alerts, and work with other Redash objects through the Redash API.

## Security First

This repository does not need your Redash URL or API key to be committed to GitHub.

- no real API key is included in this repo
- no private Redash URL is hardcoded in this repo
- `.env.example` only contains placeholders
- you add your own Redash connection details locally on your machine

You can provide credentials in either of these ways:

- environment variables such as `REDASH_URL` and `REDASH_API_KEY`
- a local JSON config file that is not committed to GitHub

## In Plain English

If you are not technical, think of this as a bridge between your AI assistant and Redash.

Without this MCP:

- your AI can only guess based on what you type
- it cannot directly look up Redash queries, dashboards, or alerts

With this MCP:

- your AI can look up real Redash data and metadata
- you can ask in normal language instead of clicking through Redash screens
- you can say things like:
  - "Show my favorite Redash queries"
  - "Run query 133822 for the last 7 days"
  - "List all dashboard tags"
  - "Create an alert when failures go above 50"

In short: this makes your AI assistant act more like a Redash power user.

## What MCP Means

MCP stands for Model Context Protocol.

It is a standard way for an AI client to talk to an external tool.

In this project:

1. Your AI client starts this server on your computer.
2. The server announces what tools it supports.
3. Your AI calls those tools when needed.
4. The server talks to Redash and returns structured results.

## What You Can Do

This server currently supports:

- Data sources: list Redash data sources
- Queries: list, search, inspect, create, update, archive, favorite, fork, execute
- Dashboards: list, inspect, create, update, archive, favorite, fork
- Alerts: list, inspect, create, update, delete, mute, manage subscriptions
- Visualizations: inspect, create, update, delete
- Widgets: list, inspect, create, update, delete
- Destinations: list alert destinations

## Prerequisites

You need:

- Python 3.10 or newer
- access to a Redash instance
- a Redash API key
- an MCP-compatible client such as Codex, Claude Code, Cursor, or another tool that can run a local stdio MCP server

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/Ashuqwe/mcp-for-redash.git
cd mcp-for-redash
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install the server

```bash
python3 -m pip install -e .
```

### 4. Prepare your Redash settings

You have two safe options.

### Option A: use environment variables

```bash
export REDASH_URL="https://your-redash.example.com"
export REDASH_API_KEY="YOUR_REDASH_API_KEY"
```

Optional:

```bash
export REDASH_TIMEOUT_SECONDS="300"
export REDASH_MCP_MAX_ROWS="1000"
```

You can copy `.env.example` as a reference, but do not commit your real `.env` file.

### Option B: use a local JSON config file

Copy [`config.example.json`](config.example.json) to a local file outside version control, for example:

```bash
mkdir -p ~/.config/redash-mcp
cp config.example.json ~/.config/redash-mcp/config.json
```

Then edit it with your own values:

```json
{
  "base_url": "https://your-redash.example.com",
  "api_key": "YOUR_REDASH_API_KEY"
}
```

If you want to store that file somewhere else, set:

```bash
export REDASH_MCP_CONFIG="/absolute/path/to/your/config.json"
```

## How To Connect It To Codex

These commands were verified against the local Codex CLI help on this machine.

### Option 1: Add it with the Codex CLI

Use the Python interpreter inside your virtual environment so Codex can always find the package:

```bash
codex mcp add redash \
  --env REDASH_URL=https://your-redash.example.com \
  --env REDASH_API_KEY=YOUR_REDASH_API_KEY \
  --env REDASH_TIMEOUT_SECONDS=300 \
  --env REDASH_MCP_MAX_ROWS=1000 \
  -- /ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python -m redash_mcp_server
```

Check that it is registered:

```bash
codex mcp list
codex mcp get redash
```

### Option 2: Add it in `~/.codex/config.toml`

```toml
[mcp_servers.redash]
command = "/ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python"
args = ["-m", "redash_mcp_server"]

[mcp_servers.redash.env]
REDASH_URL = "https://your-redash.example.com"
REDASH_API_KEY = "YOUR_REDASH_API_KEY"
REDASH_TIMEOUT_SECONDS = "300"
REDASH_MCP_MAX_ROWS = "1000"
```

## How To Connect It To Claude Code

These instructions follow Anthropic's official Claude Code MCP docs for local stdio servers.

### Option 1: Add it with the Claude CLI

```bash
claude mcp add --transport stdio \
  --env REDASH_URL=https://your-redash.example.com \
  --env REDASH_API_KEY=YOUR_REDASH_API_KEY \
  --env REDASH_TIMEOUT_SECONDS=300 \
  --env REDASH_MCP_MAX_ROWS=1000 \
  redash \
  -- /ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python -m redash_mcp_server
```

Check it:

```bash
claude mcp list
claude mcp get redash
```

Inside Claude Code, you can also use:

```text
/mcp
```

### Option 2: Add it as a project-scoped `.mcp.json`

```json
{
  "mcpServers": {
    "redash": {
      "command": "/ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python",
      "args": ["-m", "redash_mcp_server"],
      "env": {
        "REDASH_URL": "https://your-redash.example.com",
        "REDASH_API_KEY": "YOUR_REDASH_API_KEY",
        "REDASH_TIMEOUT_SECONDS": "300",
        "REDASH_MCP_MAX_ROWS": "1000"
      }
    }
  }
}
```

## How To Connect It To Cursor Or Other MCP Clients

Many MCP clients accept a JSON config with a command, args, and env block.

Example:

```json
{
  "mcpServers": {
    "redash": {
      "command": "/ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python",
      "args": ["-m", "redash_mcp_server"],
      "env": {
        "REDASH_URL": "https://your-redash.example.com",
        "REDASH_API_KEY": "YOUR_REDASH_API_KEY",
        "REDASH_TIMEOUT_SECONDS": "300",
        "REDASH_MCP_MAX_ROWS": "1000"
      }
    }
  }
}
```

If your client supports only HTTP MCP servers, this repo is not the right fit out of the box. This server uses `stdio`.

## How To Use It Once Connected

Once the MCP is installed, you usually do not call tools manually. You just ask your AI assistant what you want.

Examples:

- "List my favorite Redash dashboards."
- "Show me the query tags we use most."
- "Run query 133822 for the last 14 days."
- "Find the dashboard called revenue-overview and summarize what it contains."
- "Create an alert for query 12345 when error_count is greater than 20."
- "Add query 67890 to my favorites."

## Good Prompts For Non-Technical Users

If you do not know Redash well, use prompts like:

- "Find the dashboard related to flight cancellations and explain it simply."
- "Show me the queries I use most often."
- "Run the sales query for last week and explain the result in simple terms."
- "What alerts already exist for failed bookings?"
- "Which dashboard tags do we use for marketing?"

## Tool Groups

This MCP exposes a fairly broad tool surface. The main groups are:

- Query tools
  - `list_queries`
  - `list_my_queries`
  - `list_recent_queries`
  - `list_favorite_queries`
  - `get_query`
  - `create_query`
  - `update_query`
  - `archive_query`
  - `add_query_favorite`
  - `remove_query_favorite`
  - `fork_query`
  - `execute_saved_query`
  - `execute_adhoc_query`
- Dashboard tools
  - `list_dashboards`
  - `list_my_dashboards`
  - `list_favorite_dashboards`
  - `get_dashboard`
  - `create_dashboard`
  - `update_dashboard`
  - `archive_dashboard`
  - `fork_dashboard`
  - `add_dashboard_favorite`
  - `remove_dashboard_favorite`
- Alert tools
  - `list_alerts`
  - `get_alert`
  - `create_alert`
  - `update_alert`
  - `delete_alert`
  - `mute_alert`
  - `get_alert_subscriptions`
  - `add_alert_subscription`
  - `remove_alert_subscription`
- Visualization and widget tools
  - `get_visualization`
  - `create_visualization`
  - `update_visualization`
  - `delete_visualization`
  - `list_widgets`
  - `get_widget`
  - `create_widget`
  - `update_widget`
  - `delete_widget`
- Metadata tools
  - `list_data_sources`
  - `get_query_tags`
  - `get_dashboard_tags`
  - `list_destinations`

## Resources

This MCP also exposes a few resources:

- `redash://data-sources`
- `redash://query/{query_id}`
- `redash://dashboard/{slug}`

Resources are useful when a client wants read-only context by URI instead of calling a tool.

## Compatibility Notes

- This project uses user-supplied local configuration only.
- It supports either environment variables or a local JSON config file.
- Some Redash deployments differ slightly from the endpoints used by the reference TypeScript project.
- This server includes a compatibility fallback for `list_my_dashboards` when `/api/dashboards/my` is missing.
- On the Redash deployment used during development, `/api/visualizations/{id}` returned HTML instead of JSON. This server now raises a clear error in that case instead of returning broken data.
- Mutating endpoints are implemented, but you should test them on your own Redash instance carefully before relying on them in production workflows.

## Troubleshooting

### Error: `redash-mcp-server: command not found`

Use the virtual environment's Python directly:

```bash
/ABSOLUTE/PATH/TO/mcp-for-redash/.venv/bin/python -m redash_mcp_server
```

### Error: authentication or permission failures from Redash

Check:

- `REDASH_URL`
- `REDASH_API_KEY`
- whether that API key has permission to read or modify the object you are targeting

### Error: the AI says the MCP server is unavailable

Check:

- the command path in your MCP configuration
- that your virtual environment still exists
- that `python3 -m pip install -e .` completed successfully
- that your AI client has the server enabled

### Error: visualization detail requests fail

Some Redash deployments do not expose visualization detail as a JSON API route. In that case the MCP returns a clear error message instead of malformed output.

## Local Development

Install for development:

```bash
python3 -m pip install -e .
```

Run tests:

```bash
python3 -m unittest discover -s tests -v
```

## Credits

This project follows the same general idea as [`suthio/redash-mcp`](https://github.com/suthio/redash-mcp), but it is implemented in Python and tailored for local stdio MCP use.
