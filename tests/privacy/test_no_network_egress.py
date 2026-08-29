"""
Automated network-isolation check, per build-reference.md Section 7
("Tests should fail the build if any unexpected external socket connection
is attempted during testing") and skills/privacy-security.md.

STATUS: VERIFIED on 2026-08-29. `pytest.ini` enables deny-by-default socket
blocking across the test suite and allows only `127.0.0.1` and `localhost`.

These tests verify that the suite-wide policy blocks non-loopback connections
and permits the scoped loopback exception. Once backend/api/ exists, extend
this to boot the app and exercise its endpoints under the same policy.
"""

import socket

import pytest
from pytest_socket import SocketConnectBlockedError

# RFC 5737 addresses are reserved for documentation and must not identify a
# real public service. pytest-socket should block the call before routing.
TEST_NET_HOSTS = ("192.0.2.1", "198.51.100.1")


def test_suite_policy_blocks_external_connections():
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client,
        pytest.warns(UserWarning, match="A test tried to use socket.socket.connect"),
        pytest.raises(SocketConnectBlockedError),
    ):
        client.connect((TEST_NET_HOSTS[0], 443))


def test_suite_policy_allows_loopback():
    """A closed local port may refuse, but the privacy policy must allow it."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client:
        client.settimeout(0.1)
        try:
            client.connect(("127.0.0.1", 9))
        except SocketConnectBlockedError:
            pytest.fail("The privacy socket policy unexpectedly blocked loopback")
        except OSError:
            pass


def test_suite_policy_blocks_a_second_external_host():
    with (
        socket.socket(socket.AF_INET, socket.SOCK_STREAM) as client,
        pytest.warns(UserWarning, match="A test tried to use socket.socket.connect"),
        pytest.raises(SocketConnectBlockedError),
    ):
        client.connect((TEST_NET_HOSTS[1], 443))
