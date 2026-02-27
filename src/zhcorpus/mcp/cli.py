"""CLI entry point for the zhcorpus MCP server.

Usage:
    zhcorpus                           # stdio mode (default, for Claude Desktop)
    zhcorpus --transport sse --web     # SSE + web dashboard
    zhcorpus -t sse -p 8743 --web     # SSE on custom port with dashboard
"""

from pathlib import Path

import click

from .server import configure, run_server


@click.command()
@click.option(
    "--transport", "-t",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport mode (default: stdio).",
)
@click.option(
    "--port", "-p",
    default=8743,
    help="Port for SSE/HTTP transport (default: 8743).",
)
@click.option(
    "--web",
    is_flag=True,
    help="Enable web dashboard (SSE/HTTP mode only).",
)
@click.option(
    "--corpus-db",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to zhcorpus.db (default: data/artifacts/zhcorpus.db).",
)
@click.option(
    "--dict-db",
    type=click.Path(exists=True, path_type=Path),
    default=None,
    help="Path to dictmaster.db (default: data/artifacts/dictmaster.db).",
)
def serve(transport: str, port: int, web: bool, corpus_db: Path, dict_db: Path) -> None:
    """Start the zhcorpus MCP server.

    Default: stdio transport (zero config for Claude Desktop/Code).
    Use --transport sse --web for the web dashboard.
    """
    configure(corpus_db=corpus_db, dict_db=dict_db)

    if web and transport != "stdio":
        from .web import add_web_routes
        from .server import mcp as mcp_instance
        add_web_routes(mcp_instance)

    run_server(transport=transport, port=port)


if __name__ == "__main__":
    serve()
