"""
Notion Sync Service

Polls a user-configured Notion database, maps custom properties to internal
task fields via a dynamic property mapping schema, and ingests new/updated pages
through the dopaPal AI ingestion pipeline.

Design principles:
  - Dynamic property mapping — decoupled from any hardcoded DB layout.
  - Failure-neutral — a single bad row never aborts the full sync.
  - Incremental sync via ``last_edited_time`` filter when ``last_synced_at`` is set.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import httpx
from sqlalchemy.orm import Session

from app.models.integration import IntegrationToken
from app.services import integration_service
from app.services.task_service import ingest_from_raw_text

logger = logging.getLogger(__name__)

NOTION_API_VERSION = "2022-06-28"
NOTION_QUERY_URL = "https://api.notion.com/v1/databases/{database_id}/query"
SYNC_INTERVAL_MINUTES = 15

DEFAULT_NOTION_SETTINGS: dict[str, Any] = {
    "notion_database_id": "",
    "last_synced_at": None,
    "property_mapping": {
        "title": "Name",
        "deadline": "Due Date",
        "interest_tag": "Tags",
    },
    "status_field": "",
    "sync_filters": {
        "ignore_completed": True,
        "completed_status_value": "Done",
    },
    "synced_page_ids": [],
}


# ---------------------------------------------------------------------------
# Token retrieval & validation
# ---------------------------------------------------------------------------


def get_token_entry(
    db: Session,
    user_id: int,
    provider: str = "notion",
) -> IntegrationToken | None:
    return (
        db.query(IntegrationToken)
        .filter(
            IntegrationToken.user_id == user_id,
            IntegrationToken.provider == provider,
        )
        .first()
    )


def get_decoded_token(token: IntegrationToken) -> str:
    return integration_service.decrypt_token(token.access_token_enc)


def validate_notion_token(db: Session, user_id: int) -> str:
    """Return a valid (decoded) Notion token or raise ``RuntimeError``.

    Notion integration tokens (API keys) are static and do not expire, so
    we only check that the record exists.
    """
    token = get_token_entry(db, user_id)
    if not token:
        raise RuntimeError("Notion integration not found for user")

    return get_decoded_token(token)


# ---------------------------------------------------------------------------
# Settings helpers
# ---------------------------------------------------------------------------


def _merge_notion_settings(stored: dict[str, Any] | None) -> dict[str, Any]:
    """Deep-merge stored settings over defaults."""
    merged: dict[str, Any] = {
        "notion_database_id": "",
        "last_synced_at": None,
        "property_mapping": dict(DEFAULT_NOTION_SETTINGS["property_mapping"]),
        "status_field": DEFAULT_NOTION_SETTINGS["status_field"],
        "sync_filters": dict(DEFAULT_NOTION_SETTINGS["sync_filters"]),
        "synced_page_ids": [],
    }

    if not stored:
        return merged

    for scalar_key in ("notion_database_id", "last_synced_at", "status_field"):
        if scalar_key in stored:
            merged[scalar_key] = stored[scalar_key]

    for nested_key in ("property_mapping", "sync_filters"):
        if nested_key in stored and isinstance(stored[nested_key], dict):
            merged[nested_key].update(stored[nested_key])

    if "synced_page_ids" in stored and isinstance(stored["synced_page_ids"], list):
        merged["synced_page_ids"] = list(stored["synced_page_ids"])

    return merged


# ---------------------------------------------------------------------------
# Notion database query  (httpx.AsyncClient)
# ---------------------------------------------------------------------------

NOTION_SEARCH_URL = "https://api.notion.com/v1/search"
NOTION_DATABASE_URL = "https://api.notion.com/v1/databases/{database_id}"


async def fetch_database_schema(
    access_token: str, database_id: str
) -> dict[str, Any]:
    """Fetch a Notion database's property schema via ``GET /databases/{id}``.

    Returns the full database object — specifically the ``properties`` dict
    where each key is a column name and the value includes ``type`` and
    the type-specific options (e.g. ``status.options``, ``select.options``).
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": NOTION_API_VERSION,
    }
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            NOTION_DATABASE_URL.format(database_id=database_id),
            headers=headers,
        )
        resp.raise_for_status()
        return resp.json()


async def fetch_accessible_databases(access_token: str) -> list[dict[str, Any]]:
    """Return all databases the integration token can access.

    Each result includes ``id`` and ``title`` (plain text).
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }
    body: dict[str, Any] = {
        "filter": {"value": "database", "property": "object"},
        "page_size": 50,
    }
    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=15) as client:
        while True:
            resp = await client.post(NOTION_SEARCH_URL, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))
            next_cursor = data.get("next_cursor")
            if not next_cursor or not data.get("has_more", False):
                break
            body["start_cursor"] = next_cursor
    return results


def _db_title(db: dict[str, Any]) -> str:
    """Extract the plain-text title from a Notion database object."""
    titles = db.get("title", [])
    if isinstance(titles, list):
        return "".join(t.get("plain_text", "") for t in titles if isinstance(t, dict)).strip()
    return "Untitled"


async def _query_notion_database(
    access_token: str,
    database_id: str,
    last_synced_at: datetime | None = None,
) -> list[dict[str, Any]]:
    """Fetch pages from a Notion database via ``POST …/query``.

    Supports incremental sync via ``last_edited_time`` filter when
    ``last_synced_at`` is populated.
    """
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Notion-Version": NOTION_API_VERSION,
        "Content-Type": "application/json",
    }

    body: dict[str, Any] = {"page_size": 100}

    if last_synced_at is not None:
        body["filter"] = {
            "timestamp": "last_edited_time",
            "last_edited_time": {
                "after": last_synced_at.isoformat(),
            },
        }

    results: list[dict[str, Any]] = []
    url = NOTION_QUERY_URL.format(database_id=database_id)

    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data = resp.json()
            results.extend(data.get("results", []))

            next_cursor = data.get("next_cursor")
            if not next_cursor or not data.get("has_more", False):
                break
            body["start_cursor"] = next_cursor

    return results


# ---------------------------------------------------------------------------
# Robust nested-object parsers
# ---------------------------------------------------------------------------


def _extract_rich_text(prop: dict[str, Any]) -> str:
    """Safely concatenate ``plain_text`` from any rich-text-ish property.

    Works for both ``type: "title"`` and ``type: "rich_text"`` properties.
    Returns empty string on any failure.
    """
    try:
        prop_type = prop.get("type", "")
        if prop_type in ("title", "rich_text"):
            segments = prop.get(prop_type, [])
        else:
            # Fallback: try both keys
            segments = prop.get("title") or prop.get("rich_text") or []
        if not isinstance(segments, list):
            return ""
        return "".join(
            s.get("plain_text", "") for s in segments if isinstance(s, dict)
        ).strip()
    except Exception:
        logger.warning("Failed to extract rich text from property", exc_info=True)
        return ""


def _parse_title_prop(prop: dict[str, Any]) -> str:
    """Extract plain text from a Notion title or rich_text property."""
    return _extract_rich_text(prop)


def _parse_date_prop(prop: dict[str, Any]) -> datetime | None:
    """Extract a datetime from a Notion date property.

    Prioritises ``end`` (final deadline) over ``start``.
    Returns ``None`` when the property is ``null`` or unparseable.
    """
    try:
        date_obj = prop.get("date")
        if not isinstance(date_obj, dict):
            return None

        iso = date_obj.get("end") or date_obj.get("start")
        if not iso or not isinstance(iso, str):
            return None

        dt = datetime.fromisoformat(iso)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError, KeyError):
        logger.warning("Failed to parse Notion date property", exc_info=True)
        return None


def _parse_select_prop(prop: dict[str, Any]) -> str | None:
    """Extract the string value from a Notion select / status / multi-select.

    Gracefully handles all three types without the caller needing to branch.
    """
    try:
        # Single select or status
        for key in ("status", "select"):
            obj = prop.get(key)
            if isinstance(obj, dict):
                name = obj.get("name")
                if isinstance(name, str) and name.strip():
                    return name.strip()

        # Multi-select
        multi = prop.get("multi_select")
        if isinstance(multi, list):
            names = [
                item.get("name", "").strip()
                for item in multi
                if isinstance(item, dict) and item.get("name")
            ]
            if names:
                return ", ".join(names)

        return None
    except Exception:
        logger.warning("Failed to parse Notion select/status property", exc_info=True)
        return None


# ---------------------------------------------------------------------------
# Row-level extraction
# ---------------------------------------------------------------------------


def _extract_task_data(
    page: dict[str, Any],
    property_mapping: dict[str, str],
) -> dict[str, Any] | None:
    """Map a Notion page's user-defined properties to an internal task dict.

    Returns ``None`` when the title cannot be resolved — the row is
    silently skipped (failure-neutral).
    """
    try:
        props = page.get("properties", {})
        if not isinstance(props, dict):
            return None
    except Exception:
        logger.warning("Failed to extract properties from Notion page", exc_info=True)
        return None

    title_col = property_mapping.get("title", "Name")
    deadline_col = property_mapping.get("deadline", "Due Date")
    tag_col = property_mapping.get("interest_tag", "Tags")

    # ── Title (required) ──────────────────────────────────────────────
    title_prop = props.get(title_col, {})
    title = _parse_title_prop(title_prop)
    if not title:
        logger.info("Skipping Notion page with empty title (id=%s)", page.get("id"))
        return None

    # ── Deadline ──────────────────────────────────────────────────────
    deadline_prop = props.get(deadline_col, {})
    deadline = _parse_date_prop(deadline_prop)
    if deadline is None:
        deadline = datetime.now(timezone.utc) + timedelta(days=7)

    # ── Interest tag ─────────────────────────────────────────────────
    tag_prop = props.get(tag_col, {})
    interest_tag = _parse_select_prop(tag_prop)

    return {
        "notion_page_id": page.get("id"),
        "title": title,
        "deadline": deadline,
        "interest_tag": interest_tag,
    }


def _should_skip_completed(
    page: dict[str, Any],
    sync_filters: dict[str, Any],
    status_field: str = "",
) -> bool:
    """Check whether a page should be skipped because it is completed."""
    if not sync_filters.get("ignore_completed", True):
        return False

    completed_value = sync_filters.get("completed_status_value", "Done")
    if not completed_value:
        return False

    try:
        props = page.get("properties", {})
        if not isinstance(props, dict):
            return False

        targets: list[tuple[str, Any]] = []
        if status_field:
            prop_value = props.get(status_field)
            if isinstance(prop_value, dict):
                targets.append((status_field, prop_value))
        else:
            targets = list(props.items())

        for _prop_name, prop_value in targets:
            if not isinstance(prop_value, dict):
                continue
            prop_type = prop_value.get("type", "")

            if prop_type in ("status", "select"):
                obj = prop_value.get(prop_type)
                if isinstance(obj, dict):
                    name = obj.get("name", "")
                    if isinstance(name, str) and name.strip().lower() == completed_value.strip().lower():
                        return True

            if prop_type == "multi_select":
                items = prop_value.get("multi_select", [])
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            name = item.get("name", "")
                            if isinstance(name, str) and name.strip().lower() == completed_value.strip().lower():
                                return True

            if prop_type == "checkbox":
                if prop_value.get("checkbox") is True:
                    return True
    except Exception:
        logger.warning("Error evaluating page completion status", exc_info=True)

    return False


# ---------------------------------------------------------------------------
# Sync orchestration
# ---------------------------------------------------------------------------


async def sync_notion(
    db: Session,
    user_id: int,
    notion_settings: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full Notion sync cycle.

    Steps
    -----
    1. Validate the integration token.
    2. Load / merge settings (database ID, property mapping, filters).
    3. Query the Notion database (incremental when ``last_synced_at`` is set).
    4. For each page: dedup, filter completion status, extract task data,
       and ingest through the dopaPal AI pipeline.
    5. Persist updated settings (synced page IDs, last_synced_at).

    Failure-neutral: individual page errors are logged and never abort the
    full sync. API-level errors (auth, HTTP 4xx/5xx) short-circuit cleanly.
    """
    logger.info("Starting Notion sync for user %d", user_id)

    # 1. Validate
    try:
        access_token = validate_notion_token(db, user_id)
    except RuntimeError as e:
        return {"success": False, "error": str(e)}

    token = get_token_entry(db, user_id)
    if not token:
        return {"success": False, "error": "Notion integration not found"}

    # 2. Settings
    settings = _merge_notion_settings(token.settings_json)
    if notion_settings:
        settings.update(notion_settings)

    database_id = settings.get("notion_database_id", "")
    if not database_id:
        return {"success": False, "error": "Notion database ID not configured in settings"}

    property_mapping = settings.get("property_mapping", {})
    sync_filters = settings.get("sync_filters", {})
    synced_page_ids: set[str] = set(settings.get("synced_page_ids", []))

    last_synced_at: datetime | None = None
    last_synced_raw = settings.get("last_synced_at")
    if isinstance(last_synced_raw, str):
        try:
            last_synced_at = datetime.fromisoformat(last_synced_raw)
        except (ValueError, TypeError):
            logger.warning("Invalid last_synced_at value, ignoring: %s", last_synced_raw)

    # 3. Query Notion
    try:
        pages = await _query_notion_database(
            access_token=access_token,
            database_id=database_id,
            last_synced_at=last_synced_at,
        )
    except httpx.HTTPStatusError as e:
        snippet = e.response.text[:300]
        return {
            "success": False,
            "error": f"Notion API HTTP {e.response.status_code}: {snippet}",
        }
    except httpx.RequestError as e:
        return {"success": False, "error": f"Notion API request failed: {e}"}

    logger.info("Fetched %d Notion page(s) for user %d", len(pages), user_id)

    # 4. Process pages
    new_count = 0
    skipped_duplicate = 0
    skipped_completed = 0
    skipped_no_title = 0
    failed = 0

    for page in pages:
        page_id = page.get("id", "")

        # Deduplicate
        if page_id in synced_page_ids:
            skipped_duplicate += 1
            continue

        # Completion filter
        if _should_skip_completed(page, sync_filters, status_field=settings.get("status_field", "")):
            skipped_completed += 1
            continue

        # Extract
        task_data = _extract_task_data(page, property_mapping)
        if task_data is None:
            skipped_no_title += 1
            continue

        # Build raw text for the AI pipeline
        raw_text = task_data["title"]
        if task_data["interest_tag"]:
            raw_text += f" [{task_data['interest_tag']}]"

        # Ingest
        try:
            ingest_from_raw_text(
                db=db,
                user_id=user_id,
                raw_text=raw_text,
                source_type="notion",
                interest_tag_override=task_data["interest_tag"],
            )
            synced_page_ids.add(page_id)
            new_count += 1
            logger.info("Synced Notion page: %s", task_data["title"])
        except Exception as e:
            logger.warning(
                "Failed to ingest Notion page %s (%s): %s",
                page_id,
                task_data["title"],
                e,
            )
            failed += 1

    # 5. Persist
    settings["last_synced_at"] = datetime.utcnow().isoformat()
    settings["synced_page_ids"] = list(synced_page_ids)
    token.settings_json = settings
    db.commit()

    result: dict[str, Any] = {
        "success": True,
        "pages_fetched": len(pages),
        "new": new_count,
        "skipped_duplicate": skipped_duplicate,
        "skipped_completed": skipped_completed,
        "skipped_no_title": skipped_no_title,
        "failed": failed,
        "synced_at": settings["last_synced_at"],
    }

    logger.info("Notion sync complete for user %d: %s", user_id, result)
    return result
