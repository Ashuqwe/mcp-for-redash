from __future__ import annotations

import unittest
from unittest.mock import patch

from redash_mcp_server.config import RedashSettings
from redash_mcp_server.redash_api import (
    RedashApiError,
    RedashClient,
    _drop_none_values,
    render_sql_template,
    trim_query_result_rows,
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


class RedashClientCompatibilityTest(unittest.TestCase):
    def setUp(self) -> None:
        settings = RedashSettings(
            base_url="https://example.com",
            api_key="test-key",
            timeout_seconds=30,
            max_rows=100,
        )
        self.client = RedashClient(settings)

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


if __name__ == "__main__":
    unittest.main()
