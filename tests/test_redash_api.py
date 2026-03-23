from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from redash_mcp_server.config import (
    RedashInstanceSettings,
    load_settings,
)
from redash_mcp_server.redash_api import (
    RedashApiError,
    RedashClient,
    _drop_none_values,
    render_sql_template,
    summarize_collection,
    summarize_dashboard,
    summarize_query,
    trim_query_result_rows,
    validate_read_only_sql,
)


class RedashApiHelpersTest(unittest.TestCase):
    def test_render_sql_template_replaces_scalars_and_date_ranges(self) -> None:
        sql = (
            "select * from events "
            "where ds between '{{date.start}}' and '{{date.end}}' "
            "and country = '{{country}}'"
        )
        rendered = render_sql_template(
            sql,
            {
                "date": {"start": "2026-03-01", "end": "2026-03-20"},
                "country": "IN",
            },
        )
        self.assertIn("2026-03-01", rendered)
        self.assertIn("2026-03-20", rendered)
        self.assertIn("IN", rendered)
        self.assertNotIn("{{", rendered)

    def test_drop_none_values_keeps_falsey_non_none_values(self) -> None:
        payload = _drop_none_values(
            {
                "name": "example",
                "empty_list": [],
                "false_value": False,
                "zero": 0,
                "missing": None,
            }
        )
        self.assertEqual(
            payload,
            {
                "name": "example",
                "empty_list": [],
                "false_value": False,
                "zero": 0,
            },
        )

    def test_trim_query_result_rows_adds_truncation_metadata(self) -> None:
        payload = {
            "query_result": {
                "data": {
                    "rows": [{"id": 1}, {"id": 2}, {"id": 3}],
                    "columns": [{"name": "id", "type": "integer"}],
                }
            }
        }
        trimmed = trim_query_result_rows(payload, max_rows=2)
        rows = trimmed["query_result"]["data"]["rows"]
        self.assertEqual(rows, [{"id": 1}, {"id": 2}])
        self.assertEqual(trimmed["query_result"]["data"]["truncated_row_count"], 1)

    def test_summarize_query_hides_full_sql_by_default(self) -> None:
        payload = summarize_query(
            {
                "id": 42,
                "name": "Revenue",
                "query": "select * from really_large_table where country = 'IN'",
                "description": "Revenue query used by the finance team.",
            }
        )
        self.assertEqual(payload["id"], 42)
        self.assertIn("query_length_chars", payload)
        self.assertNotIn("query_preview", payload)

    def test_summarize_dashboard_limits_widget_list(self) -> None:
        payload = summarize_dashboard(
            {
                "id": 7,
                "slug": "ops-overview",
                "widgets": [
                    {"id": 1, "width": 1},
                    {"id": 2, "width": 2},
                    {"id": 3, "width": 3},
                ],
            },
            max_widgets=2,
        )
        self.assertEqual(payload["widgets_count"], 3)
        self.assertEqual(payload["truncated_widgets_count"], 1)
        self.assertEqual(len(payload["widgets"]), 2)

    def test_summarize_collection_tracks_truncation(self) -> None:
        payload = summarize_collection(
            [{"id": 1}, {"id": 2}, {"id": 3}],
            item_mapper=lambda item: {"id": item["id"]},
            limit=2,
        )
        self.assertEqual(payload["count"], 3)
        self.assertEqual(payload["returned_count"], 2)
        self.assertEqual(payload["truncated_count"], 1)

    def test_validate_read_only_sql_allows_select_and_blocks_mutations(self) -> None:
        validate_read_only_sql("SELECT * FROM bookings")
        validate_read_only_sql("WITH cte AS (SELECT 1) SELECT * FROM cte")

        with self.assertRaises(RedashApiError):
            validate_read_only_sql("DELETE FROM bookings")

        with self.assertRaises(RedashApiError):
            validate_read_only_sql("SELECT 1; DROP TABLE users")


class ConfigSecurityTest(unittest.TestCase):
    def test_load_settings_supports_multiple_instances(self) -> None:
        config_body = """
        {
          "default_instance": "prod",
          "instances": {
            "prod": {
              "base_url": "https://prod.example.com",
              "api_key": "prod-key"
            },
            "staging": {
              "base_url": "https://staging.example.com",
              "api_key": "staging-key"
            }
          }
        }
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.json"
            config_path.write_text(config_body)
            env = {
                "REDASH_MCP_CONFIG": str(config_path),
            }
            with patch.dict(os.environ, env, clear=True):
                settings = load_settings()

        self.assertEqual(settings.default_instance, "prod")
        self.assertEqual(sorted(settings.instances), ["prod", "staging"])
        self.assertTrue(settings.read_only)
        self.assertFalse(settings.allow_adhoc_sql)


class RedashClientCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        self.client = RedashClient(
            RedashInstanceSettings(
                name="default",
                base_url="https://example.com",
                api_key="test-key",
            ),
            timeout_seconds=30,
        )

    def test_list_my_dashboards_falls_back_when_endpoint_missing(self) -> None:
        dashboard_pages = [
            {
                "count": 3,
                "results": [
                    {"id": 1, "user_id": 99, "slug": "mine-1"},
                    {"id": 2, "user_id": 7, "slug": "other"},
                    {"id": 3, "user_id": 99, "slug": "mine-2"},
                ],
            }
        ]

        with (
            patch.object(
                self.client,
                "_paginated_get",
                side_effect=RedashApiError("missing", status_code=404),
            ),
            patch.object(
                self.client,
                "_request",
                return_value={"user": {"id": 99}},
            ),
            patch.object(
                self.client,
                "list_dashboards",
                side_effect=dashboard_pages,
            ),
        ):
            payload = self.client.list_my_dashboards(page=1, page_size=10)

        self.assertEqual(payload["count"], 2)
        self.assertEqual(
            [item["slug"] for item in payload["results"]],
            ["mine-1", "mine-2"],
        )

    def test_get_visualization_raises_clear_error_on_non_json_response(self) -> None:
        with patch.object(self.client, "_request", return_value="<html>...</html>"):
            with self.assertRaises(RedashApiError) as context:
                self.client.get_visualization(123)

        self.assertIn("non-JSON response", str(context.exception))

    def test_request_error_sanitizes_redash_response_body(self) -> None:
        response = Mock()
        response.status_code = 403
        response.text = "database password is secret"
        response.content = b"database password is secret"
        response.headers = {"content-type": "text/plain"}
        response.raise_for_status.side_effect = requests.HTTPError("403 Client Error")

        with patch.object(self.client.session, "request", return_value=response):
            with self.assertRaises(RedashApiError) as context:
                self.client._request("GET", "/api/queries")

        message = str(context.exception)
        self.assertIn("status 403", message)
        self.assertIn("GET /api/queries", message)
        self.assertNotIn("database password is secret", message)


if __name__ == "__main__":
    unittest.main()
