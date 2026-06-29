"""Open a blank page on the 9222 Chrome via raw CDP so Playwright connect has a target."""
import json
import urllib.request
import urllib.parse


def main():
    # The /json/new endpoint (PUT) creates a new tab.
    url = "http://localhost:9222/json/new?" + urllib.parse.quote("about:blank", safe="")
    try:
        req = urllib.request.Request(url, method="PUT")
        r = json.load(urllib.request.urlopen(req, timeout=8))
        print("created:", r.get("type"), r.get("url"), r.get("id"))
    except Exception as e:  # noqa: BLE001
        print("PUT /json/new failed:", repr(e)[:160])
        # Fallback: GET (older Chrome)
        try:
            r = json.load(urllib.request.urlopen("http://localhost:9222/json/new", timeout=8))
            print("created(GET):", r.get("type"), r.get("url"), r.get("id"))
        except Exception as e2:  # noqa: BLE001
            print("GET /json/new failed:", repr(e2)[:160])
            return 1
    data = json.load(urllib.request.urlopen("http://localhost:9222/json/list", timeout=5))
    print("now targets:", len(data))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
