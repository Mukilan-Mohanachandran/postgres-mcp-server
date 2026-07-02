from psql_mcp.sql import obfuscate_password


def test_obfuscate_none_or_empty():
    assert obfuscate_password("") == ""
    assert obfuscate_password(None) is None


def test_obfuscate_postgresql_url():
    url = "postgresql://user:secret@localhost:5432/mydatabase"
    result = obfuscate_password(url)
    assert result is not None
    assert "secret" not in result
    assert "****" in result
    assert result == "postgresql://user:****@localhost:5432/mydatabase"


def test_obfuscate_in_error_message():
    error_msg = "connection string: postgresql://admin:topsecret@localhost:5432/mydb"
    obfuscated = obfuscate_password(error_msg)
    assert obfuscated is not None
    assert "topsecret" not in obfuscated
    assert "postgresql://admin:****@localhost:5432/mydb" in obfuscated


def test_obfuscate_connection_params():
    conn_string = "host=localhost port=5432 dbname=mydb user=admin password=secret123"
    obfuscated = obfuscate_password(conn_string)
    assert obfuscated is not None
    assert "secret123" not in obfuscated
    assert "password=****" in obfuscated
