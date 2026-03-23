from __future__ import annotations

import time
from typing import Any

import requests

from .config import RedashSettings


DEFAULT_LIST_LIMIT = 25
DEFAULT_TEXT_PREVIEW_CHARS = 240


class RedashApiError(RuntimeError):
    """Raised when Redash returns an error or an unexpected payload."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RedashClient:
    """Small Redash API client for the MCP server."""

    def __init__(self, settings: RedashSettings) -> None:
        self.settings = settings
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Key {settings.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(
            method=method,
            url=f"{self.settings.base_url}{path}",
            timeout=self.settings.timeout_seconds,
            **kwargs,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            body = response.text.strip()
            message = f"{exc}"
            if body:
                message = f"{message}\nResponse body: {body}"
            raise RedashApiError(message, status_code=response.status_code) from exc

        if not response.content:
            return None
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            return response.json()
        return response.text

    def list_data_sources(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/data_sources")
        return payload if isinstance(payload, list) else []

    def list_queries(
        self,
        *,
        search: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"page": page, "page_size": page_size}
        if search:
            params["q"] = search
        return self._request("GET", "/api/queries", params=params)

    def list_my_queries(self, *, page: int = 1, page_size: int = 25) -> dict[str, Any]:
        return self._paginated_get("/api/queries/my", page=page, page_size=page_size)

    def list_recent_queries(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self._paginated_get("/api/queries/recent", page=page, page_size=page_size)

    def list_favorite_queries(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self._paginated_get(
            "/api/queries/favorites",
            page=page,
            page_size=page_size,
        )

    def get_query_tags(self) -> dict[str, Any]:
        return self._request("GET", "/api/queries/tags")

    def get_query(self, query_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/queries/{query_id}")

    def create_query(
        self,
        *,
        name: str,
        data_source_id: int,
        query: str,
        description: str | None = None,
        options: dict[str, Any] | None = None,
        schedule: dict[str, Any] | None = None,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "name": name,
                "data_source_id": data_source_id,
                "query": query,
                "description": description if description is not None else "",
                "options": options if options is not None else {},
                "schedule": schedule,
                "tags": tags if tags is not None else [],
            }
        )
        return self._request("POST", "/api/queries", json=payload)

    def update_query(
        self,
        query_id: int,
        *,
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
        payload = _drop_none_values(
            {
                "name": name,
                "data_source_id": data_source_id,
                "query": query,
                "description": description,
                "options": options,
                "schedule": schedule,
                "tags": tags,
                "is_archived": is_archived,
                "is_draft": is_draft,
            }
        )
        if not payload:
            raise RedashApiError("update_query requires at least one field to change.")
        return self._request("POST", f"/api/queries/{query_id}", json=payload)

    def archive_query(self, query_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/queries/{query_id}")
        return {"success": True, "query_id": query_id}

    def add_query_favorite(self, query_id: int) -> dict[str, Any]:
        self._request("POST", f"/api/queries/{query_id}/favorite")
        return {"success": True, "query_id": query_id}

    def remove_query_favorite(self, query_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/queries/{query_id}/favorite")
        return {"success": True, "query_id": query_id}

    def fork_query(self, query_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/queries/{query_id}/fork")

    def list_dashboards(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self._paginated_get("/api/dashboards", page=page, page_size=page_size)

    def list_my_dashboards(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        try:
            return self._paginated_get(
                "/api/dashboards/my",
                page=page,
                page_size=page_size,
            )
        except RedashApiError as exc:
            if exc.status_code != 404:
                raise
            return self._list_my_dashboards_fallback(page=page, page_size=page_size)

    def list_favorite_dashboards(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self._paginated_get(
            "/api/dashboards/favorites",
            page=page,
            page_size=page_size,
        )

    def get_dashboard_tags(self) -> dict[str, Any]:
        return self._request("GET", "/api/dashboards/tags")

    def get_dashboard(self, slug: str) -> dict[str, Any]:
        return self._request("GET", f"/api/dashboards/{slug}")

    def create_dashboard(
        self,
        *,
        name: str,
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "name": name,
                "tags": tags if tags is not None else [],
            }
        )
        return self._request("POST", "/api/dashboards", json=payload)

    def update_dashboard(
        self,
        dashboard_id: int,
        *,
        name: str | None = None,
        tags: list[str] | None = None,
        is_archived: bool | None = None,
        is_draft: bool | None = None,
        dashboard_filters_enabled: bool | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "name": name,
                "tags": tags,
                "is_archived": is_archived,
                "is_draft": is_draft,
                "dashboard_filters_enabled": dashboard_filters_enabled,
            }
        )
        if not payload:
            raise RedashApiError(
                "update_dashboard requires at least one field to change."
            )
        return self._request("POST", f"/api/dashboards/{dashboard_id}", json=payload)

    def archive_dashboard(self, dashboard_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/dashboards/{dashboard_id}")
        return {"success": True, "dashboard_id": dashboard_id}

    def fork_dashboard(self, dashboard_id: int) -> dict[str, Any]:
        return self._request("POST", f"/api/dashboards/{dashboard_id}/fork")

    def add_dashboard_favorite(self, dashboard_id: int) -> dict[str, Any]:
        self._request("POST", f"/api/dashboards/{dashboard_id}/favorite")
        return {"success": True, "dashboard_id": dashboard_id}

    def remove_dashboard_favorite(self, dashboard_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/dashboards/{dashboard_id}/favorite")
        return {"success": True, "dashboard_id": dashboard_id}

    def list_alerts(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/alerts")
        return payload if isinstance(payload, list) else []

    def get_alert(self, alert_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/alerts/{alert_id}")

    def create_alert(
        self,
        *,
        name: str,
        query_id: int,
        options: dict[str, Any],
        rearm: int | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "name": name,
                "query_id": query_id,
                "options": options,
                "rearm": rearm,
            }
        )
        return self._request("POST", "/api/alerts", json=payload)

    def update_alert(
        self,
        alert_id: int,
        *,
        name: str | None = None,
        query_id: int | None = None,
        options: dict[str, Any] | None = None,
        rearm: int | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "name": name,
                "query_id": query_id,
                "options": options,
                "rearm": rearm,
            }
        )
        if not payload:
            raise RedashApiError("update_alert requires at least one field to change.")
        return self._request("POST", f"/api/alerts/{alert_id}", json=payload)

    def delete_alert(self, alert_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/alerts/{alert_id}")
        return {"success": True, "alert_id": alert_id}

    def mute_alert(self, alert_id: int) -> dict[str, Any]:
        self._request("POST", f"/api/alerts/{alert_id}/mute")
        return {"success": True, "alert_id": alert_id}

    def get_alert_subscriptions(self, alert_id: int) -> list[dict[str, Any]]:
        payload = self._request("GET", f"/api/alerts/{alert_id}/subscriptions")
        return payload if isinstance(payload, list) else []

    def add_alert_subscription(
        self,
        alert_id: int,
        *,
        destination_id: int | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values({"destination_id": destination_id})
        return self._request(
            "POST",
            f"/api/alerts/{alert_id}/subscriptions",
            json=payload,
        )

    def remove_alert_subscription(
        self,
        alert_id: int,
        subscription_id: int,
    ) -> dict[str, Any]:
        self._request("DELETE", f"/api/alerts/{alert_id}/subscriptions/{subscription_id}")
        return {
            "success": True,
            "alert_id": alert_id,
            "subscription_id": subscription_id,
        }

    def get_visualization(self, visualization_id: int) -> dict[str, Any]:
        payload = self._request("GET", f"/api/visualizations/{visualization_id}")
        if isinstance(payload, dict):
            return payload
        raise RedashApiError(
            "Visualization endpoint returned a non-JSON response. "
            "This Redash deployment may not expose "
            f"/api/visualizations/{visualization_id} as a JSON API route."
        )

    def create_visualization(
        self,
        *,
        query_id: int,
        type: str,
        name: str,
        options: dict[str, Any],
        description: str | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "query_id": query_id,
                "type": type,
                "name": name,
                "description": description,
                "options": options,
            }
        )
        return self._request("POST", "/api/visualizations", json=payload)

    def update_visualization(
        self,
        visualization_id: int,
        *,
        type: str | None = None,
        name: str | None = None,
        description: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "type": type,
                "name": name,
                "description": description,
                "options": options,
            }
        )
        if not payload:
            raise RedashApiError(
                "update_visualization requires at least one field to change."
            )
        return self._request(
            "POST",
            f"/api/visualizations/{visualization_id}",
            json=payload,
        )

    def delete_visualization(self, visualization_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/visualizations/{visualization_id}")
        return {"success": True, "visualization_id": visualization_id}

    def list_widgets(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/widgets")
        return payload if isinstance(payload, list) else []

    def get_widget(self, widget_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/widgets/{widget_id}")

    def create_widget(
        self,
        *,
        dashboard_id: int,
        width: int,
        visualization_id: int | None = None,
        text: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "dashboard_id": dashboard_id,
                "visualization_id": visualization_id,
                "text": text,
                "width": width,
                "options": options if options is not None else {},
            }
        )
        return self._request("POST", "/api/widgets", json=payload)

    def update_widget(
        self,
        widget_id: int,
        *,
        visualization_id: int | None = None,
        text: str | None = None,
        width: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload = _drop_none_values(
            {
                "visualization_id": visualization_id,
                "text": text,
                "width": width,
                "options": options,
            }
        )
        if not payload:
            raise RedashApiError("update_widget requires at least one field to change.")
        return self._request("POST", f"/api/widgets/{widget_id}", json=payload)

    def delete_widget(self, widget_id: int) -> dict[str, Any]:
        self._request("DELETE", f"/api/widgets/{widget_id}")
        return {"success": True, "widget_id": widget_id}

    def list_destinations(self) -> list[dict[str, Any]]:
        payload = self._request("GET", "/api/destinations")
        return payload if isinstance(payload, list) else []

    def execute_saved_query(
        self,
        query_id: int,
        *,
        parameters: dict[str, Any] | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        if parameters or refresh:
            payload = {
                "parameters": parameters or {},
                "max_age": 0 if refresh else self.settings.timeout_seconds,
            }
            started = self._request("POST", f"/api/queries/{query_id}/results", json=payload)
            result_id = self._resolve_query_result_id(started)
            return self._request("GET", f"/api/query_results/{result_id}")
        return self._request("GET", f"/api/queries/{query_id}/results")

    def execute_adhoc_query(
        self,
        *,
        sql: str,
        data_source_id: int,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        rendered_sql = render_sql_template(sql, parameters or {})
        started = self._request(
            "POST",
            "/api/query_results",
            json={"query": rendered_sql, "data_source_id": data_source_id, "max_age": 0},
        )
        result_id = self._resolve_query_result_id(started)
        return self._request("GET", f"/api/query_results/{result_id}")

    def _resolve_query_result_id(self, payload: dict[str, Any]) -> int:
        query_result = payload.get("query_result")
        if isinstance(query_result, dict) and "id" in query_result:
            return int(query_result["id"])

        job = payload.get("job")
        if not isinstance(job, dict) or "id" not in job:
            raise RedashApiError(
                "Redash did not return a query_result or job payload."
            )

        job_id = job["id"]
        deadline = time.monotonic() + self.settings.timeout_seconds
        while time.monotonic() < deadline:
            job_payload = self._request("GET", f"/api/jobs/{job_id}").get("job", {})
            status = job_payload.get("status")
            if status == 3:
                query_result_id = job_payload.get("query_result_id")
                if query_result_id is None:
                    raise RedashApiError(
                        f"Redash job {job_id} completed without a query_result_id."
                    )
                return int(query_result_id)
            if status == 4:
                raise RedashApiError(
                    f"Redash job {job_id} failed: "
                    f"{job_payload.get('error') or job_payload}"
                )
            time.sleep(2)
        raise RedashApiError(
            f"Timed out waiting for Redash job {job_id} after "
            f"{self.settings.timeout_seconds} seconds."
        )

    def _paginated_get(
        self,
        path: str,
        *,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        return self._request(
            "GET",
            path,
            params={"page": page, "page_size": page_size},
        )

    def _list_my_dashboards_fallback(
        self,
        *,
        page: int,
        page_size: int,
    ) -> dict[str, Any]:
        current_user = self._request("GET", "/api/session").get("user", {})
        current_user_id = current_user.get("id")
        if current_user_id is None:
            raise RedashApiError(
                "Could not determine the current Redash user for the "
                "list_my_dashboards fallback."
            )

        filtered_results: list[dict[str, Any]] = []
        scan_page = 1
        scan_page_size = 100

        while True:
            payload = self.list_dashboards(page=scan_page, page_size=scan_page_size)
            results = payload.get("results") or []
            if not results:
                break

            filtered_results.extend(
                item
                for item in results
                if isinstance(item, dict) and item.get("user_id") == current_user_id
            )

            count = payload.get("count")
            if not isinstance(count, int):
                break
            if scan_page * scan_page_size >= count:
                break
            scan_page += 1

        start = max(page - 1, 0) * page_size
        end = start + page_size
        return {
            "count": len(filtered_results),
            "page": page,
            "page_size": page_size,
            "results": filtered_results[start:end],
        }


def render_sql_template(sql: str, params: dict[str, Any]) -> str:
    rendered = sql
    for key, value in params.items():
        if isinstance(value, dict):
            start = value.get("start")
            end = value.get("end")
            if start is not None:
                rendered = rendered.replace(f"{{{{{key}.start}}}}", str(start))
            if end is not None:
                rendered = rendered.replace(f"{{{{{key}.end}}}}", str(end))
            continue
        rendered = rendered.replace(f"{{{{{key}}}}}", str(value))
    return rendered


def _drop_none_values(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in payload.items() if value is not None}


def trim_query_result_rows(payload: dict[str, Any], max_rows: int) -> dict[str, Any]:
    query_result = payload.get("query_result")
    if not isinstance(query_result, dict):
        return payload
    data = query_result.get("data")
    if not isinstance(data, dict):
        return payload
    rows = data.get("rows")
    if not isinstance(rows, list):
        return payload
    if len(rows) <= max_rows:
        return payload

    trimmed = dict(payload)
    trimmed_query_result = dict(query_result)
    trimmed_data = dict(data)
    trimmed_data["rows"] = rows[:max_rows]
    trimmed_data["truncated_row_count"] = len(rows) - max_rows
    trimmed_query_result["data"] = trimmed_data
    trimmed["query_result"] = trimmed_query_result
    return trimmed


def truncate_text(value: Any, max_chars: int = DEFAULT_TEXT_PREVIEW_CHARS) -> str | None:
    if not isinstance(value, str):
        return None
    compact = " ".join(value.split())
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3] + "..."


def summarize_collection(
    items: list[dict[str, Any]],
    *,
    item_mapper,
    limit: int = DEFAULT_LIST_LIMIT,
) -> dict[str, Any]:
    safe_limit = max(limit, 1)
    sliced = items[:safe_limit]
    return {
        "count": len(items),
        "returned_count": len(sliced),
        "truncated_count": max(len(items) - len(sliced), 0),
        "results": [item_mapper(item) for item in sliced],
    }


def summarize_paginated_collection(
    payload: dict[str, Any],
    *,
    item_mapper,
    limit: int | None = None,
) -> dict[str, Any]:
    results = payload.get("results")
    if not isinstance(results, list):
        return payload
    sliced = results[: max(limit or len(results), 1)]
    return {
        "count": payload.get("count", len(results)),
        "page": payload.get("page", 1),
        "page_size": payload.get("page_size", payload.get("pageSize", len(results))),
        "returned_count": len(sliced),
        "truncated_count": max(len(results) - len(sliced), 0),
        "results": [item_mapper(item) for item in sliced if isinstance(item, dict)],
    }


def summarize_data_source(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_values(
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "paused": item.get("paused"),
            "view_only": item.get("view_only"),
            "syntax": item.get("syntax"),
        }
    )


def summarize_visualization(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_values(
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
            "query_id": item.get("query_id"),
            "description": truncate_text(item.get("description")),
        }
    )


def summarize_query(item: dict[str, Any], *, include_preview: bool = False) -> dict[str, Any]:
    visualizations = item.get("visualizations")
    summarized_visualizations = None
    if isinstance(visualizations, list):
        summarized_visualizations = [
            summarize_visualization(viz) for viz in visualizations if isinstance(viz, dict)
        ]

    payload = {
        "id": item.get("id"),
        "name": item.get("name"),
        "description": truncate_text(item.get("description")),
        "data_source_id": item.get("data_source_id"),
        "is_archived": item.get("is_archived"),
        "is_draft": item.get("is_draft"),
        "is_favorite": item.get("is_favorite"),
        "tags": item.get("tags"),
        "updated_at": item.get("updated_at"),
        "runtime": item.get("runtime"),
        "query_length_chars": len(item.get("query", "")) if isinstance(item.get("query"), str) else None,
        "query_preview": truncate_text(item.get("query"), 400) if include_preview else None,
        "visualizations": summarized_visualizations,
    }
    return _drop_none_values(payload)


def summarize_dashboard(item: dict[str, Any], *, max_widgets: int = 10) -> dict[str, Any]:
    widgets = item.get("widgets")
    summarized_widgets = None
    truncated_widgets_count = None
    if isinstance(widgets, list):
        sliced = widgets[:max(max_widgets, 1)]
        summarized_widgets = [
            summarize_widget(widget) for widget in sliced if isinstance(widget, dict)
        ]
        truncated_widgets_count = max(len(widgets) - len(sliced), 0)

    return _drop_none_values(
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "slug": item.get("slug"),
            "tags": item.get("tags"),
            "is_archived": item.get("is_archived"),
            "is_draft": item.get("is_draft"),
            "dashboard_filters_enabled": item.get("dashboard_filters_enabled"),
            "updated_at": item.get("updated_at"),
            "widgets_count": len(widgets) if isinstance(widgets, list) else None,
            "truncated_widgets_count": truncated_widgets_count,
            "widgets": summarized_widgets,
        }
    )


def summarize_alert(item: dict[str, Any]) -> dict[str, Any]:
    options = item.get("options")
    if not isinstance(options, dict):
        options = {}
    return _drop_none_values(
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "query_id": item.get("query_id"),
            "state": item.get("state"),
            "last_triggered_at": item.get("last_triggered_at"),
            "rearm": item.get("rearm"),
            "muted": options.get("muted"),
            "column": options.get("column"),
            "op": options.get("op"),
            "value": options.get("value"),
        }
    )


def summarize_widget(item: dict[str, Any]) -> dict[str, Any]:
    visualization = item.get("visualization")
    return _drop_none_values(
        {
            "id": item.get("id"),
            "dashboard_id": item.get("dashboard_id"),
            "visualization_id": item.get("visualization_id")
            or (visualization.get("id") if isinstance(visualization, dict) else None),
            "width": item.get("width"),
            "text_preview": truncate_text(item.get("text")),
            "visualization": summarize_visualization(visualization)
            if isinstance(visualization, dict)
            else None,
        }
    )


def summarize_destination(item: dict[str, Any]) -> dict[str, Any]:
    return _drop_none_values(
        {
            "id": item.get("id"),
            "name": item.get("name"),
            "type": item.get("type"),
        }
    )
