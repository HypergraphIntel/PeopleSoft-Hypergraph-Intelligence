#!/usr/bin/env python3
"""Smoke-test shared admin shell pages with headless Chrome.

This intentionally uses only the Python standard library. It talks to Chrome's
DevTools websocket directly so we can catch JavaScript runtime exceptions that
ordinary curl/py_compile checks miss.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request


DEFAULT_PAGES = [
    ("/admin/", ".pe-home", False, True),
    ("/admin/runtime", "#paneSessions", True, True),
    ("/admin/sqlws", "#sqlInput", True, True),
    ("/admin/ib", "#detailContent", True, True),
    ("/admin/envcompare", "#fieldRec", False, True),
    ("/admin/graph", "#objectType", True, False),
    ("/admin/object", "#objectType", True, False),
]


class DevTools:
    def __init__(self, ws_url: str):
        rest = ws_url.removeprefix("ws://")
        hostport, path = rest.split("/", 1)
        self.hostport = hostport
        self.host, port = hostport.split(":")
        self.port = int(port)
        self.path = "/" + path
        self.sock = socket.create_connection((self.host, self.port), timeout=5)
        self.counter = 0
        self.events: list[dict] = []
        self._handshake()

    def close(self) -> None:
        try:
            self.sock.close()
        except OSError:
            pass

    def _handshake(self) -> None:
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        request = (
            f"GET {self.path} HTTP/1.1\r\n"
            f"Host: {self.hostport}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            "Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(request.encode("ascii"))
        response = self.sock.recv(4096)
        status = response.split(b"\r\n", 1)[0]
        if b"101" not in status:
            raise RuntimeError(f"DevTools websocket handshake failed: {status!r}")

    def send(self, method: str, params: dict | None = None) -> int:
        self.counter += 1
        payload = json.dumps({
            "id": self.counter,
            "method": method,
            "params": params or {},
        }).encode("utf-8")

        header = bytearray([0x81])
        size = len(payload)
        if size < 126:
            header.append(0x80 | size)
        elif size < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", size))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", size))

        mask = os.urandom(4)
        header.extend(mask)
        masked = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.sock.sendall(header + masked)
        return self.counter

    def recv(self, timeout: float = 10) -> dict:
        self.sock.settimeout(timeout)
        while True:
            b1 = self.sock.recv(1)
            if not b1:
                raise EOFError("DevTools websocket closed")
            b2 = self.sock.recv(1)[0]
            opcode = b1[0] & 0x0F
            masked = b2 & 0x80
            size = b2 & 0x7F
            if size == 126:
                size = struct.unpack("!H", self.sock.recv(2))[0]
            elif size == 127:
                size = struct.unpack("!Q", self.sock.recv(8))[0]
            mask = self.sock.recv(4) if masked else b""
            data = b""
            while len(data) < size:
                data += self.sock.recv(size - len(data))
            if masked:
                data = bytes(byte ^ mask[i % 4] for i, byte in enumerate(data))
            if opcode == 1:
                return json.loads(data.decode("utf-8"))

    def call(self, method: str, params: dict | None = None, timeout: float = 10) -> dict:
        message_id = self.send(method, params)
        while True:
            msg = self.recv(timeout)
            if "method" in msg:
                self.events.append(msg)
            if msg.get("id") == message_id:
                return msg


def chrome_path(explicit: str | None) -> str:
    if explicit:
        return explicit
    for name in ("google-chrome-stable", "google-chrome", "chromium", "chromium-browser"):
        path = shutil.which(name)
        if path:
            return path
    raise SystemExit("No Chrome/Chromium binary found; pass --chrome /path/to/chrome")


def wait_for_target(port: int, timeout: float = 10) -> str:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{port}/json", timeout=1) as res:
                targets = json.load(res)
            for target in targets:
                if target.get("type") == "page" and target.get("webSocketDebuggerUrl"):
                    return target["webSocketDebuggerUrl"]
        except Exception:
            time.sleep(0.1)
    raise RuntimeError("Timed out waiting for Chrome DevTools target")


def event_errors(events: list[dict]) -> list[str]:
    errors: list[str] = []
    for event in events:
        method = event.get("method")
        params = event.get("params", {})
        if method == "Runtime.exceptionThrown":
            details = params.get("exceptionDetails", {})
            text = details.get("text") or "Runtime exception"
            exc = details.get("exception", {})
            desc = exc.get("description") or exc.get("value") or ""
            errors.append(f"{text}: {desc}".strip())
        elif method == "Log.entryAdded":
            entry = params.get("entry", {})
            if entry.get("level") in {"error", "warning"}:
                errors.append(f"{entry.get('level')}: {entry.get('text')}")
    return errors


def evaluate_page(
    devtools: DevTools,
    base_url: str,
    path: str,
    selector: str,
    expects_env: bool,
    expects_active_nav: bool,
) -> dict:
    devtools.events.clear()
    url = base_url.rstrip("/") + path
    devtools.call("Page.navigate", {"url": url})
    deadline = time.time() + 10
    while time.time() < deadline:
        result = devtools.call(
            "Runtime.evaluate",
            {
                "expression": "({ href: location.href, readyState: document.readyState })",
                "returnByValue": True,
            },
            timeout=2,
        )
        state = result.get("result", {}).get("result", {}).get("value") or {}
        href = state.get("href", "")
        ready_state = state.get("readyState")
        if href.startswith(url) and ready_state in {"interactive", "complete"}:
            break
        time.sleep(0.1)

    # Let page startup promises, shell env sync, and eager list loaders settle.
    time.sleep(1.2)
    expression = f"""
(() => {{
  const selector = {json.dumps(selector)};
  return {{
    path: {json.dumps(path)},
    title: document.title,
    readyState: document.readyState,
    brandCount: document.querySelectorAll('.ds-brand').length,
    activeNavCount: document.querySelectorAll('.ds-nav-link.ds-active').length,
    envSelectCount: document.querySelectorAll('.ds-env-sel').length,
    markerFound: !!document.querySelector(selector),
    bodyText: document.body ? document.body.innerText.slice(0, 500) : ''
  }};
}})()
"""
    result = devtools.call(
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True},
        timeout=5,
    )
    value = result.get("result", {}).get("result", {}).get("value") or {}
    value["eventErrors"] = event_errors(devtools.events)
    value["expectsEnv"] = expects_env
    value["expectsActiveNav"] = expects_active_nav
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8088")
    parser.add_argument("--chrome")
    parser.add_argument("--port", type=int, default=9333)
    args = parser.parse_args()

    chrome = chrome_path(args.chrome)
    profile = tempfile.mkdtemp(prefix="deathstar-chrome-")
    proc = subprocess.Popen(
        [
            chrome,
            "--headless=new",
            "--no-sandbox",
            "--disable-gpu",
            f"--remote-debugging-port={args.port}",
            f"--user-data-dir={profile}",
            "about:blank",
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    devtools: DevTools | None = None
    try:
        ws_url = wait_for_target(args.port)
        devtools = DevTools(ws_url)
        devtools.call("Page.enable")
        devtools.call("Runtime.enable")
        devtools.call("Log.enable")

        failures = []
        for path, marker, expects_env, expects_active_nav in DEFAULT_PAGES:
            result = evaluate_page(
                devtools,
                args.base_url,
                path,
                marker,
                expects_env,
                expects_active_nav,
            )
            page_failures = []
            if result.get("brandCount") != 1:
                page_failures.append(f"expected one .ds-brand, got {result.get('brandCount')}")
            if expects_active_nav and result.get("activeNavCount", 0) < 1:
                page_failures.append("missing active nav link")
            if expects_env and result.get("envSelectCount", 0) < 1:
                page_failures.append("missing shared env selector")
            if not result.get("markerFound"):
                page_failures.append(f"missing marker selector {marker!r}")
            if result.get("eventErrors"):
                page_failures.extend(result["eventErrors"])
            if page_failures:
                failures.append((path, page_failures, result))
                print(f"FAIL {path}")
                for failure in page_failures:
                    print(f"  - {failure}")
            else:
                print(f"OK   {path}")

        if failures:
            return 1
        return 0
    finally:
        if devtools:
            devtools.close()
        proc.terminate()
        try:
            _, stderr = proc.communicate(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            _, stderr = proc.communicate(timeout=3)
        shutil.rmtree(profile, ignore_errors=True)
        if proc.returncode not in {0, -15, -9, None} and stderr:
            print(stderr, file=sys.stderr)


if __name__ == "__main__":
    raise SystemExit(main())
