# Notion Integration Setup

## Prerequisites

1. Notion account
2. Integration created at notion.so/my-integrations

## Steps

1. Go to https://www.notion.so/my-integrations
2. Click **New integration**
3. Name: "Nexus H1"
4. Select workspace
5. Copy **Internal Integration Token**
6. Add to `.env`:
   ```
   NOTION_TOKEN=secret_xxxxxxxx
   ```
7. **Share databases/pages** with the integration:
   - Open database/page in Notion
   - Click **...** (menu) → **Add connections** → Select "Nexus H1"

## Usage

### Search

```bash
python integrations/notion.py search "Projects"
```

### Create Page

```python
from integrations.notion import create_page, title_prop, rich_text_prop, date_prop, todo_block

page = create_page(
    parent_id="database_id",
    properties={
        "Name": title_prop("New Task"),
        "Status": select_prop("In Progress"),
        "Due Date": date_prop("2026-05-10"),
    },
    icon="✅",
    content_blocks=[
        todo_block("Subtask 1"),
        todo_block("Subtask 2", checked=True),
    ]
)
```

### Query Database

```python
from integrations.notion import query_database

tasks = query_database(
    "database_id",
    filter_criteria={
        "property": "Status",
        "select": {"equals": "In Progress"}
    }
)
```

## Common Use Cases

- **Daily notes**: Auto-create daily journal pages
- **Task management**: Sync tasks from other sources
- **Knowledge base**: Store summaries and insights
- **Meeting notes**: Auto-format meeting summaries
