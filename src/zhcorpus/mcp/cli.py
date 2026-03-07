"""CLI entry point for the zhcorpus MCP server.

Usage:
    zhcorpus                           # stdio mode (default, for Claude Code)
    zhcorpus --transport sse --web     # SSE + web dashboard
    zhcorpus -t sse -p 8743 --web     # SSE on custom port with dashboard
"""

from pathlib import Path

import click

from .server import configure, create_server, make_sse_and_streamable_http_app, mcp


@click.command()
@click.option(
    "--transport", "-t",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport mode (default: stdio).",
)
@click.option(
    "--port", "-p",
    default=8744,
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

    Default: stdio transport (zero config for Claude Code).
    Use --transport sse --web for the web dashboard.
    """
    configure(corpus_db=corpus_db, dict_db=dict_db)
    server = create_server()

    if transport == "sse":
        server.settings.host = "127.0.0.1"
        server.settings.port = port

        if web:
            from .web import add_web_routes
            add_web_routes(mcp)

        # Serve both SSE and Streamable HTTP on the same port
        # (Cursor tries Streamable HTTP first, then SSE)
        import anyio
        import uvicorn

        app = make_sse_and_streamable_http_app(mount_path="/")
        config = uvicorn.Config(
            app,
            host=server.settings.host,
            port=server.settings.port,
            log_level=server.settings.log_level.lower(),
        )

        async def _run():
            srv = uvicorn.Server(config)
            await srv.serve()

        anyio.run(_run)
        return
    elif web:
        click.echo("--web requires --transport sse; ignoring --web.", err=True)

    server.run(transport=transport)


if __name__ == "__main__":
    serve()
