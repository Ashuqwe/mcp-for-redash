from __future__ import annotations

from typing import Any

from mcp.server.fastmcp import FastMCP

from .config import load_settings
from .redash_api import RedashClient, trim_query_result_rows


settings = load_settings()
client = RedashClient(settings)
mcp = FastMCP("Redash MCP", json_response=True)


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


@mcp.tool()
def list_data_sources() -> list[dict[str, Any]]:
    """List available Redash data sources."""
    return client.list_data_sources()


@mcp.tool()
def list_queries(
    search: str | None = None,
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List Redash queries with optional search text."""
    return client.list_queries(search=search, page=page, page_size=page_size)


@mcp.tool()
def list_my_queries(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List queries owned by the current Redash user."""
    return client.list_my_queries(page=page, page_size=page_size)


@mcp.tool()
def list_recent_queries(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List recent Redash queries."""
    return client.list_recent_queries(page=page, page_size=page_size)


@mcp.tool()
def list_favorite_queries(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List favorite Redash queries."""
    return client.list_favorite_queries(page=page, page_size=page_size)


@mcp.tool()
def get_query_tags() -> dict[str, Any]:
    """List Redash query tags."""
    return client.get_query_tags()


@mcp.tool()
def get_query(query_id: int) -> dict[str, Any]:
    """Fetch a saved Redash query definition."""
    return client.get_query(query_id)


@mcp.tool()
def create_query(
    name: str,
    data_source_id: int,
    query: str,
    description: str | None = None,
    options: dict[str, Any] | None = None,
    schedule: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a saved Redash query."""
    return client.create_query(
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
) -> dict[str, Any]:
    """Update fields on a saved Redash query."""
    return client.update_query(
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
def archive_query(query_id: int) -> dict[str, Any]:
    """Archive a saved Redash query."""
    return client.archive_query(query_id)


@mcp.tool()
def add_query_favorite(query_id: int) -> dict[str, Any]:
    """Add a query to the current user's favorites."""
    return client.add_query_favorite(query_id)


@mcp.tool()
def remove_query_favorite(query_id: int) -> dict[str, Any]:
    """Remove a query from the current user's favorites."""
    return client.remove_query_favorite(query_id)


@mcp.tool()
def fork_query(query_id: int) -> dict[str, Any]:
    """Fork a saved Redash query."""
    return client.fork_query(query_id)


@mcp.tool()
def list_dashboards(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List Redash dashboards."""
    return client.list_dashboards(page=page, page_size=page_size)


@mcp.tool()
def list_my_dashboards(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List dashboards owned by the current Redash user."""
    return client.list_my_dashboards(page=page, page_size=page_size)


@mcp.tool()
def list_favorite_dashboards(
    page: int = 1,
    page_size: int = 25,
) -> dict[str, Any]:
    """List favorite Redash dashboards."""
    return client.list_favorite_dashboards(page=page, page_size=page_size)


@mcp.tool()
def get_dashboard_tags() -> dict[str, Any]:
    """List Redash dashboard tags."""
    return client.get_dashboard_tags()


@mcp.tool()
def create_dashboard(
    name: str,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Create a Redash dashboard."""
    return client.create_dashboard(name=name, tags=tags)


@mcp.tool()
def update_dashboard(
    dashboard_id: int,
    name: str | None = None,
    tags: list[str] | None = None,
    is_archived: bool | None = None,
    is_draft: bool | None = None,
    dashboard_filters_enabled: bool | None = None,
) -> dict[str, Any]:
    """Update fields on a Redash dashboard."""
    return client.update_dashboard(
        dashboard_id,
        name=name,
        tags=tags,
        is_archived=is_archived,
        is_draft=is_draft,
        dashboard_filters_enabled=dashboard_filters_enabled,
    )


@mcp.tool()
def archive_dashboard(dashboard_id: int) -> dict[str, Any]:
    """Archive a Redash dashboard."""
    return client.archive_dashboard(dashboard_id)


@mcp.tool()
def fork_dashboard(dashboard_id: int) -> dict[str, Any]:
    """Fork a Redash dashboard."""
    return client.fork_dashboard(dashboard_id)


@mcp.tool()
def add_dashboard_favorite(dashboard_id: int) -> dict[str, Any]:
    """Add a dashboard to the current user's favorites."""
    return client.add_dashboard_favorite(dashboard_id)


@mcp.tool()
def remove_dashboard_favorite(dashboard_id: int) -> dict[str, Any]:
    """Remove a dashboard from the current user's favorites."""
    return client.remove_dashboard_favorite(dashboard_id)


@mcp.tool()
def get_dashboard(slug: str) -> dict[str, Any]:
    """Fetch a Redash dashboard by slug."""
    return client.get_dashboard(slug)


@mcp.tool()
def list_alerts() -> list[dict[str, Any]]:
    """List Redash alerts."""
    return client.list_alerts()


@mcp.tool()
def get_alert(alert_id: int) -> dict[str, Any]:
    """Fetch a Redash alert by id."""
    return client.get_alert(alert_id)


@mcp.tool()
def create_alert(
    name: str,
    query_id: int,
    options: dict[str, Any],
    rearm: int | None = None,
) -> dict[str, Any]:
    """Create a Redash alert."""
    return client.create_alert(
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
) -> dict[str, Any]:
    """Update a Redash alert."""
    return client.update_alert(
        alert_id,
        name=name,
        query_id=query_id,
        options=options,
        rearm=rearm,
    )


@mcp.tool()
def delete_alert(alert_id: int) -> dict[str, Any]:
    """Delete a Redash alert."""
    return client.delete_alert(alert_id)


@mcp.tool()
def mute_alert(alert_id: int) -> dict[str, Any]:
    """Mute a Redash alert."""
    return client.mute_alert(alert_id)


@mcp.tool()
def get_alert_subscriptions(alert_id: int) -> list[dict[str, Any]]:
    """List subscriptions for a Redash alert."""
    return client.get_alert_subscriptions(alert_id)


@mcp.tool()
def add_alert_subscription(
    alert_id: int,
    destination_id: int | None = None,
) -> dict[str, Any]:
    """Add a subscription to a Redash alert."""
    return client.add_alert_subscription(
        alert_id,
        destination_id=destination_id,
    )


@mcp.tool()
def remove_alert_subscription(
    alert_id: int,
    subscription_id: int,
) -> dict[str, Any]:
    """Remove a Redash alert subscription."""
    return client.remove_alert_subscription(alert_id, subscription_id)


@mcp.tool()
def get_visualization(visualization_id: int) -> dict[str, Any]:
    """Fetch a Redash visualization by id."""
    return client.get_visualization(visualization_id)


@mcp.tool()
def create_visualization(
    query_id: int,
    type: str,
    name: str,
    options: dict[str, Any],
    description: str | None = None,
) -> dict[str, Any]:
    """Create a Redash visualization."""
    return client.create_visualization(
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
) -> dict[str, Any]:
    """Update a Redash visualization."""
    return client.update_visualization(
        visualization_id,
        type=type,
        name=name,
        description=description,
        options=options,
    )


@mcp.tool()
def delete_visualization(visualization_id: int) -> dict[str, Any]:
    """Delete a Redash visualization."""
    return client.delete_visualization(visualization_id)


@mcp.tool()
def list_widgets() -> list[dict[str, Any]]:
    """List Redash widgets."""
    return client.list_widgets()


@mcp.tool()
def get_widget(widget_id: int) -> dict[str, Any]:
    """Fetch a Redash widget by id."""
    return client.get_widget(widget_id)


@mcp.tool()
def create_widget(
    dashboard_id: int,
    width: int,
    visualization_id: int | None = None,
    text: str | None = None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a Redash widget."""
    return client.create_widget(
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
) -> dict[str, Any]:
    """Update a Redash widget."""
    return client.update_widget(
        widget_id,
        visualization_id=visualization_id,
        text=text,
        width=width,
        options=options,
    )


@mcp.tool()
def delete_widget(widget_id: int) -> dict[str, Any]:
    """Delete a Redash widget."""
    return client.delete_widget(widget_id)


@mcp.tool()
def list_destinations() -> list[dict[str, Any]]:
    """List Redash destinations."""
    return client.list_destinations()


@mcp.tool()
def execute_saved_query(
    query_id: int,
    parameters: dict[str, Any] | None = None,
    date_param: str | None = None,
    date_start: str | None = None,
    date_end: str | None = None,
    refresh: bool = False,
) -> dict[str, Any]:
    """Execute a saved query and return structured results."""
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
) -> dict[str, Any]:
    """Execute ad hoc SQL against a Redash data source."""
    normalized = _normalize_parameters(parameters, date_param, date_start, date_end)
    payload = client.execute_adhoc_query(
        sql=sql,
        data_source_id=data_source_id,
        parameters=normalized or None,
    )
    return trim_query_result_rows(payload, settings.max_rows)


@mcp.resource("redash://data-sources")
def data_sources_resource() -> list[dict[str, Any]]:
    """Expose the Redash data source catalog as a resource."""
    return client.list_data_sources()


@mcp.resource("redash://query/{query_id}")
def query_resource(query_id: str) -> dict[str, Any]:
    """Expose a saved Redash query as a resource."""
    return client.get_query(int(query_id))


@mcp.resource("redash://dashboard/{slug}")
def dashboard_resource(slug: str) -> dict[str, Any]:
    """Expose a Redash dashboard as a resource."""
    return client.get_dashboard(slug)


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
