"""Run the complete CoolRoute API + frontend server on Windows and macOS."""
from __future__ import annotations

import socket
import webbrowser

import uvicorn


def find_free_port() -> int:
    for port in range(8765, 8770):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("Ports 8765–8769 are busy. Close an old CoolRoute server and try again.")


class CoolRouteServer(uvicorn.Server):
    def __init__(self, config: uvicorn.Config, url: str):
        super().__init__(config)
        self.coolroute_url = url

    async def startup(self, sockets=None) -> None:
        await super().startup(sockets=sockets)
        if self.started:
            print(f"CoolRoute is ready. Use this exact URL: {self.coolroute_url}", flush=True)
            webbrowser.open_new_tab(self.coolroute_url)


def main() -> int:
    port = find_free_port()
    url = f"http://127.0.0.1:{port}/"
    print(f"Starting CoolRoute API server at {url}", flush=True)
    print("Leave this window open. Press Ctrl+C here to stop the app.", flush=True)
    # Uvicorn owns the main thread, avoiding Windows event-loop/signal issues.
    # Open the browser only after the API and app lifespan have started.
    try:
        server = CoolRouteServer(uvicorn.Config(
            "api_server:app", host="127.0.0.1", port=port,
            log_level="info", access_log=True,
        ), url)
        server.run()
    except KeyboardInterrupt:
        print("Stopping CoolRoute…", flush=True)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", flush=True)
        raise SystemExit(1)
