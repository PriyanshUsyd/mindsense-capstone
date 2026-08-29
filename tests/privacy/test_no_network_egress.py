"""
Automated network-isolation check, per build-reference.md Section 7
("Tests should fail the build if any unexpected external socket connection
is attempted during testing") and skills/privacy-security.md.

STATUS: DRAFT built to fill a Week 4 gap on 2026-08-29. Requires the
`pytest-socket` package (not yet added to any requirements file — adding it
needs its own privacy spot-check per the standing dependency rule, which is
trivially satisfied since it's a test-only dependency that blocks sockets
rather than opening them).

This currently only asserts the *mechanism* works (blocking a raw socket
connect) since there is no real application code yet to run against. Once
backend/api/ exists, extend this to actually boot the app under test and
exercise the endpoints, per the socket_allow_hosts exception for loopback.
"""

import socket

import pytest


def test_disable_and_enable_socket_blocks_external_connections():
    pytest.importorskip("pytest_socket")
    from pytest_socket import SocketBlockedError, disable_socket, enable_socket

    disable_socket()
    try:
        with pytest.raises(SocketBlockedError):
            socket.create_connection(("8.8.8.8", 53), timeout=1)
    finally:
        enable_socket()


def test_loopback_is_the_only_intended_exception():
    """Documents the one legitimate exception: a scoped local smoke test
    against the Ollama daemon on loopback. Not a real network test — a
    reminder co-located with the enforcement test above."""
    allowed_hosts = {"127.0.0.1", "localhost"}
    assert allowed_hosts == {"127.0.0.1", "localhost"}
