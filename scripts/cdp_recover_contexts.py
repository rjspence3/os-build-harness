"""Recover a wedged CDP connection by disposing orphaned (non-default) browser contexts.

A prior `browser.new_context()` over CDP on Chrome 147+ leaks an incognito browser
context that Playwright's connect_over_cdp then trips over (Browser.setDownloadBehavior
-> 'Browser context management is not supported'). This talks raw CDP over the browser
websocket to enumerate browser contexts and dispose the extra ones, restoring connect.

Uses only the websocket URL from /json/version (no Playwright). Safe: only disposes
contexts beyond the first (the default user context is not in getBrowserContexts output;
incognito/created contexts are). Does not close the browser.
"""
import json
import urllib.request

from playwright.sync_api import sync_playwright


def get_ws_url():
    v = json.load(urllib.request.urlopen("http://localhost:9222/json/version", timeout=5))
    return v["webSocketDebuggerUrl"]


def main():
    # Use Playwright's bundled websocket via a minimal CDP session is awkward; instead
    # use the sync websocket from playwright's _impl is not public. Fall back to the
    # 'websocket' stdlib-ish client if available; otherwise use a tiny raw client.
    try:
        from websocket import create_connection
    except Exception:  # noqa: BLE001
        print("websocket-client not available; trying playwright CDP session route")
        return _via_playwright()

    ws = create_connection(get_ws_url(), max_size=None)
    _id = 0

    def call(method, params=None):
        nonlocal _id
        _id += 1
        ws.send(json.dumps({"id": _id, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(ws.recv())
            if msg.get("id") == _id:
                return msg

    res = call("Target.getBrowserContexts")
    ctxs = res.get("result", {}).get("browserContextIds", [])
    print("orphan browser contexts:", ctxs)
    for cid in ctxs:
        r = call("Target.disposeBrowserContext", {"browserContextId": cid})
        print("disposed", cid, "->", r.get("result", r.get("error")))
    ws.close()
    print("done")
    return 0


def _via_playwright():
    # Last resort: connect_over_cdp may still partially work to enumerate contexts.
    p = sync_playwright().start()
    try:
        b = p.chromium.connect_over_cdp("http://localhost:9222")
        print("contexts:", len(b.contexts))
        for c in b.contexts[1:]:
            try:
                c.close()
                print("closed an extra context")
            except Exception as e:  # noqa: BLE001
                print("close err", repr(e)[:120])
    finally:
        p.stop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
