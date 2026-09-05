"""Transport privacy regressions using synthetic data and loopback only."""

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from urllib import request

import pytest

from backend.slm.client import SLMUnavailableError, UrllibLoopbackTransport


@pytest.mark.parametrize("status", [301, 302, 303, 307, 308])
def test_transport_does_not_follow_redirects(status):
    paths = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            paths.append(self.path)
            self.send_response(status)
            self.send_header(
                "Location", f"http://127.0.0.1:{self.server.server_port}/redirected"
            )
            self.end_headers()

        def do_GET(self):
            paths.append(self.path)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b'{"unexpected_redirect": true}')

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with pytest.raises(SLMUnavailableError):
            UrllibLoopbackTransport().post_json(
                f"http://127.0.0.1:{server.server_port}/api/chat",
                {"synthetic": True},
                2.0,
            )
        assert paths == ["/api/chat"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_transport_rejects_external_endpoint_before_constructing_opener(monkeypatch):
    def must_not_open(*args, **kwargs):
        pytest.fail("Invalid endpoints must be rejected before transport setup")

    monkeypatch.setattr(request, "build_opener", must_not_open)
    with pytest.raises(ValueError, match="loopback"):
        UrllibLoopbackTransport().post_json(
            "http://198.51.100.1/api/chat", {"synthetic": True}, 2.0
        )


def test_transport_explicitly_disables_environment_proxies(monkeypatch):
    handlers_seen = []

    class StopOpener:
        def open(self, *args, **kwargs):
            raise OSError("synthetic connection failure")

    def capture_opener(*handlers):
        handlers_seen.extend(handlers)
        return StopOpener()

    monkeypatch.setattr(request, "build_opener", capture_opener)
    with pytest.raises(SLMUnavailableError):
        UrllibLoopbackTransport().post_json(
            "http://127.0.0.1:11434/api/chat", {"synthetic": True}, 2.0
        )
    proxy_handlers = [h for h in handlers_seen if isinstance(h, request.ProxyHandler)]
    assert len(proxy_handlers) == 1
    assert proxy_handlers[0].proxies == {}
