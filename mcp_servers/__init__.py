"""
MCP Servers package.

Contiene i server MCP (Model Context Protocol) che espongono
tool per gli agenti:

- web_search_mcp: Ricerca web e news via DuckDuckGo
- file_reader_mcp: Lettura documenti (PDF, DOCX, TXT)
- report_writer_mcp: Generazione report (MD, HTML, JSON)
"""

from .web_search_mcp import mcp as web_search_server
from .file_reader_mcp import mcp as file_reader_server
from .report_writer_mcp import mcp as report_writer_server

__all__ = [
    "web_search_server",
    "file_reader_server", 
    "report_writer_server"
]
