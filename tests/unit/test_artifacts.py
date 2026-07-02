from psql_mcp.artifacts import format_query_result


def test_format_query_result_truncates_rows():
    rows = [{"id": i, "name": f"user-{i}"} for i in range(5)]
    result = format_query_result(rows, max_rows=3, max_cell_chars=100, execution_ms=10)
    assert result["row_count"] == 3
    assert result["truncated"] is True
    assert len(result["rows"]) == 3


def test_format_query_result_truncates_cell_chars():
    rows = [{"note": "x" * 100}]
    result = format_query_result(rows, max_rows=10, max_cell_chars=20, execution_ms=5)
    cell = result["rows"][0][0]
    assert len(cell) == 20
    assert cell.endswith("...")


def test_format_query_result_empty():
    result = format_query_result([], max_rows=10, max_cell_chars=100, execution_ms=1)
    assert result["columns"] == []
    assert result["rows"] == []
    assert result["row_count"] == 0
