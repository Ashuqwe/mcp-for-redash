from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .redash_api import (
    DEFAULT_LIST_LIMIT,
    RedashApiError,
    RedashClient,
    summarize_alert,
    summarize_collection,
    summarize_dashboard,
    summarize_data_source,
    summarize_destination,
    summarize_paginated_collection,
    summarize_query,
    summarize_visualization,
    summarize_widget,
    trim_query_result_rows,
    validate_read_only_sql,
)


settings = load_settings()
clients = {
    name: RedashClient(instance, timeout_seconds=settings.timeout_seconds)
    for name, instance in settings.instances.items()
}
mcp = FastMCP("Redash MCP", json_response=True)


def _get_client(instance: str | None = None) -> RedashClient:
    selected = settings.get_instance(instance)
    return clients[selected.name]


def _normalize_parameters(
    parameters: dict[str, Any] | None,
    date_param: str | None,
    date_start: str | None,
    date_end: str | None,
) -> dict[str, Any]:
    normalized = dict(parameters or {})
    if any([date_param, date_start, date_end]):
        if not all([date_param, date_start, date_end]):
            raise ValueError(
                "date_param, date_start, and date_end must be supplied together."
            )
        normalized[date_param] = {"start": date_start, "end": date_end}
    return normalized


def _require_mutations_enabled(action: str) -> None:
    if settings.read_only:
        raise RedashApiError(
            f"{action} is disabled because REDASH_MCP_READ_ONLY is enabled."
        )


def _require_adhoc_sql_enabled() -> None:
    if not settings.allow_adhoc_sql:
        raise RedashApiError(
            "Ad hoc SQL execution is disabled. Set REDASH_MCP_ALLOW_ADHOC_SQL=true "
            "to enable it."
        )


def _validate_query_text(query: str) -> None:
    validate_read_only_sql(query)


def _validate_saved_query_execution(client: RedashClient, query_id: int) -> None:
    query_payload = client.get_query(query_id)
    query_text = query_payload.get("query")
    if not isinstance(query_text, str):
        raise RedashApiError(
            f"Saved query {query_id} does not expose SQL text for validation."
        )
    validate_read_only_sql(query_text)


@mcp.tool()
def list_redash_instances() -> dict[str, Any]:
    """List configured Redash instances."""
    return {
        "default_instance": settings.default_instance,
        "instances": sorted(settings.instances),
        "read_only": settings.read_only,
        "allow_adhoc_sql": settings.allow_adhoc_sql,
    }


@mcp.tool()
def list_data_sources(instance: str | None = None) -> dict[str, Any]:
    """List available Redash data sources."""
    return summarize_collection(
        _get_client(instance).list_data_sources(),
        item_mapper=summarize_data_source,
        limit=DEFAULT_LIST_LIMIT,
    )


@mcp.tool()
def list_queries(
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List Redash queries with optional search text."""
    payload = _get_client(instance).list_queries(
        search=search,
        page=page,
        page_size=page_size,
    )
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_query)


@mcp.tool()
def list_my_queries(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List queries owned by the current Redash user."""
    payload = _get_client(instance).list_my_queries(page=page, page_size=page_size)
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_query)


@mcp.tool()
def list_recent_queries(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List recent Redash queries."""
    payload = _get_client(instance).list_recent_queries(
        page=page,
        page_size=page_size,
    )
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_query)


@mcp.tool()
def list_favorite_queries(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List favorite Redash queries."""
    payload = _get_client(instance).list_favorite_queries(
        page=page,
        page_size=page_size,
    )
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_query)


@mcp.tool()
def get_query_tags(instance: str | None = None) -> dict[str, Any]:
    """List Redash query tags."""
    return _get_client(instance).get_query_tags()


@mcp.tool()
def get_query(
    query_id: int,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """Fetch a saved Redash query definition."""
    payload = _get_client(instance).get_query(query_id)
    if full:
        return payload
    return summarize_query(payload, include_preview=True)


@mcp.tool()
def create_query(
    name: str,
    data_source_id: int,
    query: str,
    description: str | None = None,
    options: dict[str, Any] | None = None,
    schedule: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a saved Redash query."""
    _require_mutations_enabled("create_query")
    _validate_query_text(query)
    return _get_client(instance).create_query(
        name=name,
        data_source_id=data_source_id,
        query=query,
        description=description,
        options=options,
        schedule=schedule,
        tags=tags,
    )


@mcp.tool()
def update_query(
    query_id: int,
    name: str | None = None,
    data_source_id: int | None = None,
    query: str | None = None,
    description: str | None = None,
    options: dict[str, Any] | None = None,
    schedule: dict[str, Any] | None = None,
    tags: list[str] | None = None,
    is_archived: bool | None = None,
    is_draft: bool | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update fields on a saved Redash query."""
    _require_mutations_enabled("update_query")
    if query is not None:
        _validate_query_text(query)
    return _get_client(instance).update_query(
        query_id,
        name=name,
        data_source_id=data_source_id,
        query=query,
        description=description,
        options=options,
        schedule=schedule,
        tags=tags,
        is_archived=is_archived,
        is_draft=is_draft,
    )


@mcp.tool()
def archive_query(query_id: int, instance: str | None = None) -> dict[str, Any]:
    """Archive a saved Redash query."""
    _require_mutations_enabled("archive_query")
    return _get_client(instance).archive_query(query_id)


@mcp.tool()
def add_query_favorite(query_id: int, instance: str | None = None) -> dict[str, Any]:
    """Add a query to the current user's favorites."""
    _require_mutations_enabled("add_query_favorite")
    return _get_client(instance).add_query_favorite(query_id)


@mcp.tool()
def remove_query_favorite(
    query_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Remove a query from the current user's favorites."""
    _require_mutations_enabled("remove_query_favorite")
    return _get_client(instance).remove_query_favorite(query_id)


@mcp.tool()
def fork_query(query_id: int, instance: str | None = None) -> dict[str, Any]:
    """Fork a saved Redash query."""
    _require_mutations_enabled("fork_query")
    return _get_client(instance).fork_query(query_id)


@mcp.tool()
def list_dashboards(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List Redash dashboards."""
    payload = _get_client(instance).list_dashboards(page=page, page_size=page_size)
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_dashboard)


@mcp.tool()
def list_my_dashboards(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List dashboards owned by the current Redash user."""
    payload = _get_client(instance).list_my_dashboards(
        page=page,
        page_size=page_size,
    )
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_dashboard)


@mcp.tool()
def list_favorite_dashboards(
    page: int = 1,
    page_size: int = 25,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """List favorite Redash dashboards."""
    payload = _get_client(instance).list_favorite_dashboards(
        page=page,
        page_size=page_size,
    )
    if full:
        return payload
    return summarize_paginated_collection(payload, item_mapper=summarize_dashboard)


@mcp.tool()
def get_dashboard_tags(instance: str | None = None) -> dict[str, Any]:
    """List Redash dashboard tags."""
    return _get_client(instance).get_dashboard_tags()


@mcp.tool()
def create_dashboard(
    name: str,
    tags: list[str] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a Redash dashboard."""
    _require_mutations_enabled("create_dashboard")
    return _get_client(instance).create_dashboard(name=name, tags=tags)


@mcp.tool()
def update_dashboard(
    dashboard_id: int,
    name: str | None = None,
    tags: list[str] | None = None,
    is_archived: bool | None = None,
    is_draft: bool | None = None,
    dashboard_filters_enabled: bool | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update fields on a Redash dashboard."""
    _require_mutations_enabled("update_dashboard")
    return _get_client(instance).update_dashboard(
        dashboard_id,
        name=name,
        tags=tags,
        is_archived=is_archived,
        is_draft=is_draft,
        dashboard_filters_enabled=dashboard_filters_enabled,
    )


@mcp.tool()
def archive_dashboard(
    dashboard_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Archive a Redash dashboard."""
    _require_mutations_enabled("archive_dashboard")
    return _get_client(instance).archive_dashboard(dashboard_id)


@mcp.tool()
def fork_dashboard(dashboard_id: int, instance: str | None = None) -> dict[str, Any]:
    """Fork a Redash dashboard."""
    _require_mutations_enabled("fork_dashboard")
    return _get_client(instance).fork_dashboard(dashboard_id)


@mcp.tool()
def add_dashboard_favorite(
    dashboard_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Add a dashboard to the current user's favorites."""
    _require_mutations_enabled("add_dashboard_favorite")
    return _get_client(instance).add_dashboard_favorite(dashboard_id)


@mcp.tool()
def remove_dashboard_favorite(
    dashboard_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Remove a dashboard from the current user's favorites."""
    _require_mutations_enabled("remove_dashboard_favorite")
    return _get_client(instance).remove_dashboard_favorite(dashboard_id)


@mcp.tool()
def get_dashboard(
    slug: str,
    full: bool = False,
    max_widgets: int = 10,
    instance: str | None = None,
) -> dict[str, Any]:
    """Fetch a Redash dashboard by slug."""
    payload = _get_client(instance).get_dashboard(slug)
    if full:
        return payload
    return summarize_dashboard(payload, max_widgets=max_widgets)


@mcp.tool()
def list_alerts(
    full: bool = False,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """List Redash alerts."""
    payload = _get_client(instance).list_alerts()
    if full:
        return payload
    return summarize_collection(payload, item_mapper=summarize_alert)


@mcp.tool()
def get_alert(
    alert_id: int,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """Fetch a Redash alert by id."""
    payload = _get_client(instance).get_alert(alert_id)
    if full:
        return payload
    return summarize_alert(payload)


@mcp.tool()
def create_alert(
    name: str,
    query_id: int,
    options: dict[str, Any],
    rearm: int | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a Redash alert."""
    _require_mutations_enabled("create_alert")
    return _get_client(instance).create_alert(
        name=name,
        query_id=query_id,
        options=options,
        rearm=rearm,
    )


@mcp.tool()
def update_alert(
    alert_id: int,
    name: str | None = None,
    query_id: int | None = None,
    options: dict[str, Any] | None = None,
    rearm: int | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update a Redash alert."""
    _require_mutations_enabled("update_alert")
    return _get_client(instance).update_alert(
        alert_id,
        name=name,
        query_id=query_id,
        options=options,
        rearm=rearm,
    )


@mcp.tool()
def delete_alert(alert_id: int, instance: str | None = None) -> dict[str, Any]:
    """Delete a Redash alert."""
    _require_mutations_enabled("delete_alert")
    return _get_client(instance).delete_alert(alert_id)


@mcp.tool()
def mute_alert(alert_id: int, instance: str | None = None) -> dict[str, Any]:
    """Mute a Redash alert."""
    _require_mutations_enabled("mute_alert")
    return _get_client(instance).mute_alert(alert_id)


@mcp.tool()
def get_alert_subscriptions(
    alert_id: int,
    instance: str | None = None,
) -> list[dict[str, Any]]:
    """List subscriptions for a Redash alert."""
    return _get_client(instance).get_alert_subscriptions(alert_id)


@mcp.tool()
def add_alert_subscription(
    alert_id: int,
    destination_id: int | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Add a subscription to a Redash alert."""
    _require_mutations_enabled("add_alert_subscription")
    return _get_client(instance).add_alert_subscription(
        alert_id,
        destination_id=destination_id,
    )


@mcp.tool()
def remove_alert_subscription(
    alert_id: int,
    subscription_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Remove a Redash alert subscription."""
    _require_mutations_enabled("remove_alert_subscription")
    return _get_client(instance).remove_alert_subscription(
        alert_id,
        subscription_id,
    )


@mcp.tool()
def get_visualization(
    visualization_id: int,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """Fetch a Redash visualization by id."""
    payload = _get_client(instance).get_visualization(visualization_id)
    if full:
        return payload
    return summarize_visualization(payload)


@mcp.tool()
def create_visualization(
    query_id: int,
    type: str,
    name: str,
    options: dict[str, Any],
    description: str | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a Redash visualization."""
    _require_mutations_enabled("create_visualization")
    return _get_client(instance).create_visualization(
        query_id=query_id,
        type=type,
        name=name,
        options=options,
        description=description,
    )


@mcp.tool()
def update_visualization(
    visualization_id: int,
    type: str | None = None,
    name: str | None = None,
    description: str | None = None,
    options: dict[str, Any] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update a Redash visualization."""
    _require_mutations_enabled("update_visualization")
    return _get_client(instance).update_visualization(
        visualization_id,
        type=type,
        name=name,
        description=description,
        options=options,
    )


@mcp.tool()
def delete_visualization(
    visualization_id: int,
    instance: str | None = None,
) -> dict[str, Any]:
    """Delete a Redash visualization."""
    _require_mutations_enabled("delete_visualization")
    return _get_client(instance).delete_visualization(visualization_id)


@mcp.tool()
def list_widgets(
    full: bool = False,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """List Redash widgets."""
    payload = _get_client(instance).list_widgets()
    if full:
        return payload
    return summarize_collection(payload, item_mapper=summarize_widget)


@mcp.tool()
def get_widget(
    widget_id: int,
    full: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """Fetch a Redash widget by id."""
    payload = _get_client(instance).get_widget(widget_id)
    if full:
        return payload
    return summarize_widget(payload)


@mcp.tool()
def create_widget(
    dashboard_id: int,
    width: int,
    visualization_id: int | None = None,
    text: str | None = None,
    options: dict[str, Any] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Create a Redash widget."""
    _require_mutations_enabled("create_widget")
    return _get_client(instance).create_widget(
        dashboard_id=dashboard_id,
        width=width,
        visualization_id=visualization_id,
        text=text,
        options=options,
    )


@mcp.tool()
def update_widget(
    widget_id: int,
    visualization_id: int | None = None,
    text: str | None = None,
    width: int | None = None,
    options: dict[str, Any] | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Update a Redash widget."""
    _require_mutations_enabled("update_widget")
    return _get_client(instance).update_widget(
        widget_id,
        visualization_id=visualization_id,
        text=text,
        width=width,
        options=options,
    )


@mcp.tool()
def delete_widget(widget_id: int, instance: str | None = None) -> dict[str, Any]:
    """Delete a Redash widget."""
    _require_mutations_enabled("delete_widget")
    return _get_client(instance).delete_widget(widget_id)


@mcp.tool()
def list_destinations(
    full: bool = False,
    instance: str | None = None,
) -> list[dict[str, Any]] | dict[str, Any]:
    """List Redash destinations."""
    payload = _get_client(instance).list_destinations()
    if full:
        return payload
    return summarize_collection(payload, item_mapper=summarize_destination)


@mcp.tool()
def execute_saved_query(
    query_id: int,
    parameters: dict[str, Any] | None = None,
    date_param: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    refresh: bool = False,
    instance: str | None = None,
) -> dict[str, Any]:
    """Execute a saved query and return structured results."""
    client = _get_client(instance)
    _validate_saved_query_execution(client, query_id)
    normalized = _normalize_parameters(parameters, date_param, date_start, date_end)
    payload = client.execute_saved_query(
        query_id,
        parameters=normalized or None,
        refresh=refresh,
    )
    return trim_query_result_rows(payload, settings.max_rows)


@mcp.tool()
def execute_adhoc_query(
    sql: str,
    data_source_id: int,
    parameters: dict[str, Any] | None = None,
    date_param: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    instance: str | None = None,
) -> dict[str, Any]:
    """Execute ad hoc SQL against a Redash data source."""
    _require_adhoc_sql_enabled()
    _validate_query_text(sql)
    normalized = _normalize_parameters(parameters, date_param, date_start, date_end)
    payload = _get_client(instance).execute_adhoc_query(
        sql=sql,
        data_source_id=data_source_id,
        parameters=normalized or None,
    )
    return trim_query_result_rows(payload, settings.max_rows)


@mcp.resource("redash://instances")
def instances_resource() -> dict[str, Any]:
    """Expose configured Redash instances as a resource."""
    return list_redash_instances()


@mcp.resource("redash://data-sources")
def data_sources_resource() -> dict[str, Any]:
    """Expose the default Redash data source catalog as a resource."""
    return summarize_collection(
        _get_client().list_data_sources(),
        item_mapper=summarize_data_source,
        limit=DEFAULT_LIST_LIMIT,
    )


@mcp.resource("redash://query/{query_id}")
def query_resource(query_id: str) -> dict[str, Any]:
    """Expose a saved Redash query from the default instance as a resource."""
    return summarize_query(_get_client().get_query(int(query_id)), include_preview=True)


@mcp.resource("redash://dashboard/{slug}")
def dashboard_resource(slug: str) -> dict[str, Any]:
    """Expose a Redash dashboard from the default instance as a resource."""
    return summarize_dashboard(_get_client().get_dashboard(slug))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
