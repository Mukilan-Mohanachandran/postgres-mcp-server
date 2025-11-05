To run this in the development mode

fastmcp dev main.py


claude config

{
  "mcpServers": {
    "psql-server": {
      "command": "C:\\Users\\mukil\\Desktop\\mcp_project\\postgres-mcp-server\\.venv\\Scripts\\python.exe",
      "args": [
        "C:\\\\Users\\\\mukil\\\\Desktop\\\\mcp_project\\\\postgres-mcp-server\\\\main.py"
      ],
      "env": {
        "DB_HOST": "localhost",
        "DB_PORT": "5432",
        "DB_NAME": "postgres",
        "DB_USER": "postgres",
        "DB_PASS": "postgres"
      },
      "cwd": "C:\\\\Users\\\\mukil\\\\Desktop\\\\mcp_project\\\\postgres-mcp-server"
    }
  },
  "preferences": {
    "menuBarEnabled": false,
    "legacyQuickEntryEnabled": false
  }
}