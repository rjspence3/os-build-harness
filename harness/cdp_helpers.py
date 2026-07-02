#!/usr/bin/env python3
# ---------------------------------------------------------------------------
# VENDORED — canonical source: kernel/scripts/cdp_helpers.py
# Vendored 2026-06-16 to remove the off-repo dependency and make the repo
# clone-clean. Sync manually if the kernel copy changes.
# This repo uses only connect_with_retry + is_chrome_available; the rest
# (Gmail/Slack/Substack/Calendar helpers) rides along unused.
# ---------------------------------------------------------------------------
"""
CDP Helper Library
Common patterns for connecting to Chrome via CDP and reading authenticated services.

Workers import this module to access Gmail, Substack, LinkedIn without re-implementing
the connection + retry logic each time.

Usage:
    from cdp_helpers import connect_with_retry, get_gmail_inbox, get_substack_posts, get_calendar_events

Chrome debug uses Profile 9 (Rob's authenticated profile dir, shared with his interactive Chrome).
If Chrome isn't running, ensure_chrome_running() will launch it on demand.

CANONICAL WORKER TOOL: Use this file for all CDP browser automation. Do NOT use:
  - authenticated-browser-cdp.py  (thin wrapper, superseded by this file)
  - authenticated_browser.py      (different strategy: persistent-profile launch, not CDP connect)
"""

import json
import os
import time
import socket
import subprocess
from datetime import date
from enum import Enum
from typing import Optional

CDP_PORT = 9222
CDP_ENDPOINT = f"http://localhost:{CDP_PORT}"
CDP_DATA_DIR = os.path.expanduser("~/Library/Application Support/Google/Chrome/Profile 9")
DEFAULT_TIMEOUT_MS = 30_000
CONNECT_RETRY_DELAY_S = 5

# Flags for on-demand Chrome launch — mirrors launch-chrome-debug.sh
_CHROME_FLAGS = [
    f"--remote-debugging-port={CDP_PORT}",
    "--remote-allow-origins=*",
    f"--user-data-dir={CDP_DATA_DIR}",
    "--disable-background-networking",
    "--disable-component-update",
    "--disable-sync",
    "--disable-client-side-phishing-detection",
    "--disable-features=OptimizationGuideModelDownloading,OptimizationHints,OptimizationGuideOnDeviceModel,MediaRouter,Translate",
    "--no-first-run",
    "--no-default-browser-check",
    "--renderer-process-limit=4",
    "--js-flags=--max-old-space-size=512",
    "--disk-cache-size=268435456",
    # Do NOT add "--enable-automation": it BREAKS Playwright CDP context management on
    # Chrome 147+. Added 2026-05-23 as a mis-fix for a CDP error, then identified 2026-05-26
    # as the actual cause of the regression (May 24 worked without it; May 25/26 failed with
    # it). Removed to match the verified-working live config. Re-adding reintroduces the bug.
]

# Gmail DOM selectors — obfuscated class names that Google can change without notice.
# If GmailSelectorError is raised, inspect Gmail manually and update these.
GMAIL_SELECTORS = {
    "verified": "2026-03-05",
    "row": "tr.zA",                 # Email row in inbox / search results
    "subject": ".y6",              # Subject text element
    "from": ".yW span[email]",     # Sender span (has name= and email= attributes)
    "date": ".xW span",            # Date element (title attr has full timestamp)
    "snippet": ".y2",              # Snippet / preview text
    "unread_class": "zE",          # Class added to row when message is unread
    # Structural fallback — doesn't depend on obfuscated names
    "row_fallback": "tr[data-legacy-thread-id]",
}


class GmailSelectorError(Exception):
    """Gmail's DOM layout has changed — selectors in GMAIL_SELECTORS need updating."""


# --- Login state detection (ported from authenticated_browser.py) ---

class LoginState(Enum):
    LOGGED_IN = "logged_in"
    LOGGED_OUT = "logged_out"
    MFA_REQUIRED = "mfa_required"
    UNKNOWN = "unknown"


_MFA_PATTERNS = [
    "verification code", "authenticator app", "two-factor", "2-factor",
    "2fa", "mfa", "one-time password", "otp", "verify your identity",
    "6-digit code", "enter the code", "check your phone", "security code",
]

_LOGGED_OUT_PATTERNS = [
    "sign in", "log in", "login", "sign up", "create account",
    "forgot password", "enter your email", "enter your password",
    "welcome back", "get started",
]


# --- Connection ---

def ensure_chrome_running() -> None:
    """Launch Chrome debug if CDP port isn't responding. Blocks until CDP is ready."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(("127.0.0.1", CDP_PORT))
    sock.close()
    if result == 0:
        return  # Already running

    subprocess.Popen(
        ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] + _CHROME_FLAGS,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for _ in range(30):  # 15 seconds max
        time.sleep(0.5)
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if sock.connect_ex(("127.0.0.1", CDP_PORT)) == 0:
            sock.close()
            return
        sock.close()
    raise RuntimeError(f"Chrome failed to start on port {CDP_PORT} within 15s")


def connect_with_retry(max_retries: int = 3):
    """Connect to Chrome debug session with retry on failure.

    Returns (playwright, browser, context) tuple. Caller is responsible for cleanup:

        p.stop()  # Disconnects Playwright without closing Chrome.

    Never call browser.close() on a CDP-connected browser — it kills the user's Chrome.

    Open tabs via `context.new_page()` on the returned context. Do NOT call
    `browser.new_context()` — that fails in Chrome 147+ over CDP. The user's
    existing context (returned here) is what you want.

    Raises RuntimeError after max_retries failed attempts.
    """
    from playwright.sync_api import sync_playwright

    ensure_chrome_running()

    last_error = None
    for attempt in range(max_retries):
        try:
            p = sync_playwright().start()
            browser = p.chromium.connect_over_cdp(CDP_ENDPOINT)
            contexts = browser.contexts
            if not contexts:
                p.stop()
                raise RuntimeError("No browser contexts found in Chrome session")
            return p, browser, contexts[0]
        except Exception as e:
            last_error = e
            if attempt < max_retries - 1:
                time.sleep(CONNECT_RETRY_DELAY_S)
            try:
                p.stop()
            except Exception:
                pass

    raise RuntimeError(f"Failed to connect to Chrome after {max_retries} attempts: {last_error}")


def is_chrome_available() -> bool:
    """Quick check if Chrome debug port is reachable."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{CDP_ENDPOINT}/json/version", timeout=3)
        return True
    except Exception:
        return False


# --- Login state detection ---

def check_login_state(url: str, authenticated_url_prefix: Optional[str] = None) -> LoginState:
    """Check login state by navigating to a URL in a new tab.

    Opens a new tab, navigates to url, inspects the result, closes the tab.
    Use this for pre-flight checks before starting a task.

    Args:
        url: URL to navigate to.
        authenticated_url_prefix: If the final URL starts with this prefix, return LOGGED_IN.
            Example: "https://mail.google.com/mail/u/0"
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
            state = check_page_login_state(page, authenticated_url_prefix)
            return state
        finally:
            page.close()
    finally:
        p.stop()


def check_page_login_state(page, authenticated_url_prefix: Optional[str] = None) -> LoginState:
    """Check login state on an already-navigated page (no extra network request).

    Use this inside a task when you already have a page open and want to detect
    whether the session is still valid before proceeding.

    Args:
        page: A Playwright Page object that has already navigated to the target URL.
        authenticated_url_prefix: If the page's current URL starts with this prefix,
            return LOGGED_IN. Example: "https://mail.google.com/mail/u/"
    """
    current_url = page.url
    page_text = page.inner_text("body").lower()

    if authenticated_url_prefix and current_url.startswith(authenticated_url_prefix):
        return LoginState.LOGGED_IN

    if any(pattern in page_text for pattern in _MFA_PATTERNS):
        return LoginState.MFA_REQUIRED

    if any(pattern in page_text for pattern in _LOGGED_OUT_PATTERNS):
        return LoginState.LOGGED_OUT

    return LoginState.UNKNOWN


# --- Gmail ---

def verify_gmail_selectors(account: int = 0) -> None:
    """Verify Gmail DOM selectors are still valid. Raises GmailSelectorError if not.

    Call this before a bulk Gmail extraction to fail fast with a clear error
    rather than silently returning empty results after a Gmail layout update.

    Does not return email data — use get_gmail_inbox() for that.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.goto(
            f"https://mail.google.com/mail/u/{account}/#inbox",
            wait_until="domcontentloaded",
            timeout=DEFAULT_TIMEOUT_MS,
        )
        page.wait_for_timeout(5000)

        try:
            page.wait_for_selector(GMAIL_SELECTORS["row"], timeout=10_000)
        except Exception:
            try:
                page.wait_for_selector(GMAIL_SELECTORS["row_fallback"], timeout=5_000)
            except Exception:
                raise GmailSelectorError(
                    f"Gmail layout changed: no email rows found with any known selector "
                    f"(last verified: {GMAIL_SELECTORS['verified']}). "
                    f"Inspect Gmail manually and update GMAIL_SELECTORS in cdp_helpers.py."
                )
            raise GmailSelectorError(
                f"Gmail layout changed: primary row selector '{GMAIL_SELECTORS['row']}' failed "
                f"but structural fallback '{GMAIL_SELECTORS['row_fallback']}' succeeded "
                f"(last verified: {GMAIL_SELECTORS['verified']}). "
                f"Update GMAIL_SELECTORS['row'] and re-verify child selectors."
            )

        page.close()
    finally:
        p.stop()


def get_gmail_inbox(
    account: int = 0,
    filter_today: bool = False,
    max_emails: int = 20,
) -> list[dict]:
    """Fetch Gmail inbox emails via authenticated Chrome session.

    Args:
        account: Gmail account (0=personal you@example.com, 1=work you@your-org.com)
        filter_today: Only return today's emails
        max_emails: Maximum number of emails to return

    Returns list of email dicts: subject, from, from_email, date, snippet, unread.
    Raises GmailSelectorError if Gmail's DOM layout has changed.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            page.goto(
                f"https://mail.google.com/mail/u/{account}/#inbox",
                wait_until="domcontentloaded",
                timeout=DEFAULT_TIMEOUT_MS,
            )
            page.wait_for_timeout(5000)

            try:
                page.wait_for_selector(GMAIL_SELECTORS["row"], timeout=DEFAULT_TIMEOUT_MS)
            except Exception as e:
                raise GmailSelectorError(
                    f"Gmail inbox row selector '{GMAIL_SELECTORS['row']}' timed out "
                    f"(last verified: {GMAIL_SELECTORS['verified']}). "
                    f"Run verify_gmail_selectors() to diagnose."
                ) from e

            emails = page.evaluate(
                """(sel) => {
                    const rows = document.querySelectorAll(sel.row);
                    const results = [];
                    for (let i = 0; i < rows.length; i++) {
                        const row = rows[i];
                        const subjectEl = row.querySelector(sel.subject);
                        const fromEl = row.querySelector(sel.from);
                        const dateEl = row.querySelector(sel.date);
                        const snippetEl = row.querySelector(sel.snippet);
                        const isUnread = row.classList.contains(sel.unread_class);
                        results.push({
                            subject: subjectEl ? subjectEl.innerText.trim() : '',
                            from: fromEl ? (fromEl.getAttribute('name') || fromEl.getAttribute('email') || '') : '',
                            from_email: fromEl ? (fromEl.getAttribute('email') || '') : '',
                            date: dateEl ? dateEl.getAttribute('title') || dateEl.innerText.trim() : '',
                            snippet: snippetEl ? snippetEl.innerText.trim() : '',
                            unread: isUnread,
                        });
                    }
                    return results;
                }""",
                GMAIL_SELECTORS,
            )
        finally:
            page.close()

        if filter_today:
            today = date.today().strftime("%-m/%d/%y")
            emails = [e for e in emails if today in e.get("date", "")]

        return emails[:max_emails]

    finally:
        p.stop()


def search_gmail(query: str, account: int = 0, max_results: int = 10) -> list[dict]:
    """Search Gmail using a query string.

    Args:
        query: Gmail search query (supports from:, to:, subject:, is:unread, etc.)
        account: Gmail account (0=personal, 1=work)
        max_results: Maximum results to return

    Raises GmailSelectorError if Gmail's DOM layout has changed.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            encoded_query = query.replace(" ", "+")
            page.goto(
                f"https://mail.google.com/mail/u/{account}/#search/{encoded_query}",
                wait_until="domcontentloaded",
                timeout=DEFAULT_TIMEOUT_MS,
            )
            page.wait_for_timeout(5000)

            try:
                page.wait_for_selector(GMAIL_SELECTORS["row"], timeout=DEFAULT_TIMEOUT_MS)
            except Exception as e:
                raise GmailSelectorError(
                    f"Gmail search row selector '{GMAIL_SELECTORS['row']}' timed out "
                    f"(last verified: {GMAIL_SELECTORS['verified']}). "
                    f"Run verify_gmail_selectors() to diagnose."
                ) from e

            emails = page.evaluate(
                """(sel) => {
                    const rows = document.querySelectorAll(sel.row);
                    const results = [];
                    for (const row of rows) {
                        const subjectEl = row.querySelector(sel.subject);
                        const fromEl = row.querySelector(sel.from);
                        const dateEl = row.querySelector(sel.date);
                        const snippetEl = row.querySelector(sel.snippet);
                        results.push({
                            subject: subjectEl ? subjectEl.innerText.trim() : '',
                            from: fromEl ? (fromEl.getAttribute('name') || fromEl.getAttribute('email') || '') : '',
                            from_email: fromEl ? (fromEl.getAttribute('email') || '') : '',
                            date: dateEl ? dateEl.getAttribute('title') || dateEl.innerText.trim() : '',
                            snippet: snippetEl ? snippetEl.innerText.trim() : '',
                            unread: row.classList.contains(sel.unread_class),
                        });
                    }
                    return results;
                }""",
                GMAIL_SELECTORS,
            )
        finally:
            page.close()
        return emails[:max_results]

    finally:
        p.stop()


def get_email_body(thread_id: str, account: int = 0) -> dict:
    """Open a Gmail thread by ID and extract the full body text.

    Args:
        thread_id: Gmail legacy thread ID (data-legacy-thread-id from row)
        account: Gmail account index (0=personal, 1=work)

    Returns dict with keys:
        subject, from, from_email, date, snippet, body (full plain text)

    The body is the concatenated text of all message parts in the thread.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            url = f"https://mail.google.com/mail/u/{account}/#inbox/{thread_id}"
            page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
            page.wait_for_timeout(4000)

            # Wait for message body to render
            try:
                page.wait_for_selector("div.a3s", timeout=DEFAULT_TIMEOUT_MS)
            except Exception:
                # Try thread view selector as fallback
                try:
                    page.wait_for_selector("div.ii.gt", timeout=5000)
                except Exception:
                    pass

            result = page.evaluate("""() => {
                // Subject
                const subjectEl = document.querySelector('h2.hP');
                const subject = subjectEl ? subjectEl.innerText.trim() : '';

                // Sender info from the expanded message header
                const fromEl = document.querySelector('span.gD');
                const fromName = fromEl ? (fromEl.getAttribute('name') || fromEl.innerText.trim()) : '';
                const fromEmail = fromEl ? (fromEl.getAttribute('email') || '') : '';

                // Date
                const dateEl = document.querySelector('span.g3');
                const date = dateEl ? dateEl.getAttribute('title') || dateEl.innerText.trim() : '';

                // Body — collect all message body divs (handles threads with multiple messages)
                const bodyEls = document.querySelectorAll('div.a3s.aiL, div.a3s');
                let body = '';
                for (const el of bodyEls) {
                    const text = el.innerText.trim();
                    if (text) body += text + '\\n\\n---\\n\\n';
                }
                body = body.replace(/---\\s*$/, '').trim();

                return { subject, from: fromName, from_email: fromEmail, date, body };
            }""")

            return result
        finally:
            page.close()
    finally:
        p.stop()


def search_gmail_with_bodies(query: str, account: int = 0, max_results: int = 10) -> list[dict]:
    """Search Gmail and return results with full email bodies.

    Like search_gmail() but clicks through each result to get the full body text.
    Slower than search_gmail (one page load per email) but provides complete content
    for amount extraction, frequency detection, and receipt vs. subscription classification.

    Returns list of dicts with all search_gmail fields plus:
        body: full plain text of the email thread
        thread_id: Gmail legacy thread ID
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            encoded_query = query.replace(" ", "+")
            page.goto(
                f"https://mail.google.com/mail/u/{account}/#search/{encoded_query}",
                wait_until="domcontentloaded",
                timeout=DEFAULT_TIMEOUT_MS,
            )
            page.wait_for_timeout(5000)

            try:
                page.wait_for_selector(GMAIL_SELECTORS["row"], timeout=DEFAULT_TIMEOUT_MS)
            except Exception as e:
                raise GmailSelectorError(
                    "Gmail search row selector timed out. Run verify_gmail_selectors() to diagnose."
                ) from e

            # Extract thread IDs and list-view metadata from the search results
            rows_meta = page.evaluate(
                """(sel) => {
                    const rows = document.querySelectorAll('tr[data-legacy-thread-id]');
                    const results = [];
                    for (const row of rows) {
                        const subjectEl = row.querySelector(sel.subject);
                        const fromEl = row.querySelector(sel.from);
                        const dateEl = row.querySelector(sel.date);
                        const snippetEl = row.querySelector(sel.snippet);
                        results.push({
                            thread_id: row.getAttribute('data-legacy-thread-id') || '',
                            subject: subjectEl ? subjectEl.innerText.trim() : '',
                            from: fromEl ? (fromEl.getAttribute('name') || fromEl.getAttribute('email') || '') : '',
                            from_email: fromEl ? (fromEl.getAttribute('email') || '') : '',
                            date: dateEl ? dateEl.getAttribute('title') || dateEl.innerText.trim() : '',
                            snippet: snippetEl ? snippetEl.innerText.trim() : '',
                            unread: row.classList.contains(sel.unread_class),
                        });
                    }
                    return results;
                }""",
                GMAIL_SELECTORS,
            )
        finally:
            page.close()

        results = []
        for meta in rows_meta[:max_results]:
            if not meta.get("thread_id"):
                meta["body"] = ""
                results.append(meta)
                continue
            try:
                detail = get_email_body(meta["thread_id"], account=account)
                meta["body"] = detail.get("body", "")
                # Prefer detail subject/from if richer
                if detail.get("subject"):
                    meta["subject"] = detail["subject"]
                if detail.get("from_email"):
                    meta["from_email"] = detail["from_email"]
            except Exception:
                meta["body"] = ""
            results.append(meta)

        return results

    finally:
        p.stop()


# --- Google Calendar ---

def get_calendar_events(account: int = 0) -> list[dict]:
    """Fetch today's events from Google Calendar via authenticated Chrome session.

    Args:
        account: Google account index (0=personal you@example.com)

    Returns list of event dicts:
        {"title": str, "start": str, "end": str, "location": str, "all_day": bool}

    Returns empty list (with a stderr warning) if not logged in.
    Google Calendar's obfuscated class names can change; selectors last verified 2026-03-08.
    """
    import sys
    p, browser, context = connect_with_retry()
    page = context.new_page()
    try:
        try:
            page.goto(
                "https://calendar.google.com/calendar/r/day",
                wait_until="domcontentloaded",
                timeout=DEFAULT_TIMEOUT_MS,
            )
            page.wait_for_timeout(4000)

            # Login check — calendar redirects to accounts.google.com if logged out
            current_url = page.url
            if "accounts.google.com" in current_url or "signin" in current_url:
                print("WARNING: Google Calendar session expired — not logged in", file=sys.stderr)
                return []

        except Exception as _nav_err:
            print(f"WARNING: Calendar navigation error: {_nav_err}", file=sys.stderr)
            return []

        # Wait for events container to appear (or time limit)
        try:
            page.wait_for_selector("[data-eventid], [data-eventchip], .KF4T6b", timeout=10_000)
        except Exception:
            # May just mean no events today — proceed to scrape
            pass

        events = page.evaluate("""() => {
            const results = [];

            // --- Timed events ---
            // Try multiple selector strategies for event chips
            const chipSelectors = [
                '[data-eventid]',
                '[data-eventchip]',
                '.KF4T6b',
            ];
            let chips = [];
            for (const sel of chipSelectors) {
                chips = Array.from(document.querySelectorAll(sel));
                if (chips.length > 0) break;
            }

            for (const chip of chips) {
                // Skip chips that are visual duplicates (e.g. resize handles)
                if (chip.getAttribute('data-eventid') && chip.closest('[data-eventid]') !== chip) continue;

                // Title
                let title = '';
                const titleSelectors = ['.gVNoLb', '.XuJrye', '[data-eventid] span', '.TFBnme'];
                for (const sel of titleSelectors) {
                    const el = chip.querySelector(sel);
                    if (el && el.innerText.trim()) { title = el.innerText.trim(); break; }
                }
                if (!title) title = chip.getAttribute('data-tooltip') || chip.innerText.trim().split('\\n')[0];

                // Time
                let startTime = '', endTime = '';
                const timeSelectors = ['.bWmBcc', '.QtqNAd', '.gVNoLb + span', 'time'];
                for (const sel of timeSelectors) {
                    const el = chip.querySelector(sel);
                    if (el && el.innerText.trim()) {
                        const timeText = el.innerText.trim();
                        const parts = timeText.split('–');
                        if (parts.length >= 2) {
                            startTime = parts[0].trim();
                            endTime = parts[1].trim();
                        } else {
                            startTime = timeText;
                        }
                        break;
                    }
                }

                // Location
                let location = '';
                const locSelectors = ['.G3LHJ', '.eoY6nd'];
                for (const sel of locSelectors) {
                    const el = chip.querySelector(sel);
                    if (el && el.innerText.trim()) { location = el.innerText.trim(); break; }
                }

                // If title came from tooltip and starts with "All day, ...", it's an all-day event
                // Tooltip format: "All day, EVENT TITLE, Calendar: CALENDAR NAME, DATE"
                let isAllDay = false;
                if (!startTime && !endTime) {
                    // No time found — likely all-day
                    isAllDay = true;
                }
                // Check both tooltip attr and title text for "All day" prefix
                const tooltip = chip.getAttribute('data-tooltip') || '';
                const fullText = tooltip || title;
                const lowerFull = fullText.toLowerCase();
                if (lowerFull.startsWith('all day,') || lowerFull.startsWith('all day ')) {
                    isAllDay = true;
                    // Extract clean title: "All day, TITLE, Calendar: ..." → TITLE
                    const withoutPrefix = fullText.replace(/^all day[, ]+/i, '');
                    const calIdx = withoutPrefix.toLowerCase().indexOf(', calendar:');
                    title = (calIdx >= 0 ? withoutPrefix.slice(0, calIdx) : withoutPrefix).trim();
                } else if (title.toLowerCase().startsWith('all day,')) {
                    isAllDay = true;
                    const withoutPrefix = title.replace(/^all day,\\s*/i, '');
                    const calIdx = withoutPrefix.toLowerCase().indexOf(', calendar:');
                    title = (calIdx >= 0 ? withoutPrefix.slice(0, calIdx) : withoutPrefix).trim();
                }

                if (title) {
                    results.push({ title, start: startTime, end: endTime, location, all_day: isAllDay });
                }
            }

            // --- All-day events ---
            // All-day events appear in a separate strip at the top
            const allDaySelectors = ['.Jmftzc [data-eventid]', '.K8Cm9d', '.YrbPuc'];
            for (const sel of allDaySelectors) {
                const allDayEls = document.querySelectorAll(sel);
                if (allDayEls.length > 0) {
                    for (const el of allDayEls) {
                        const titleEl = el.querySelector('.gVNoLb, .XuJrye') || el;
                        const title = titleEl.innerText.trim().split('\\n')[0];
                        if (title && !results.find(r => r.title === title)) {
                            results.push({ title, start: '', end: '', location: '', all_day: true });
                        }
                    }
                    break;
                }
            }

            return results;
        }""")
        return events
    finally:
        page.close()
        p.stop()


# --- Substack ---

def get_substack_posts(limit: int = 10) -> list[dict]:
    """Fetch recent Substack posts from the user's feed.

    Returns list of post dicts: title, publication, date, url, teaser.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            page.goto("https://substack.com/inbox", wait_until="networkidle", timeout=DEFAULT_TIMEOUT_MS)
            page.wait_for_selector("div.reader2-post-container", timeout=DEFAULT_TIMEOUT_MS)

            posts = page.evaluate("""() => {
                // Updated 2026-04-06: Substack removed child class selectors (a.post-preview-title,
                // a.pub-name, .post-preview-description, time). Container selector still works.
                // Now using innerText parsing + a[href*='/p/'] for URLs.
                const containers = document.querySelectorAll('div.reader2-post-container');
                const results = [];
                for (const c of containers) {
                    // URL extraction: reliable via href pattern
                    const urlEl = c.querySelector('a[href*="/p/"]');
                    const url = urlEl ? urlEl.href : '';

                    // Full text extraction + heuristic parsing
                    const fullText = c.innerText.trim();
                    const lines = fullText.split('\\n')
                        .map(l => l.trim())
                        .filter(l => l.length > 0);

                    // Line 0: publication (usually short, may be all-caps)
                    const publication = lines[0] || '';
                    // Title: first line longer than 20 chars and under 150 chars
                    const title = lines.find(l => l.length > 20 && l.length < 150) || '';
                    // Description: next qualifying line after title
                    const description = lines.find(l =>
                        l.length > 30 &&
                        l.length < 200 &&
                        l !== title &&
                        l !== publication
                    ) || '';
                    // Date: look for lines matching date patterns (e.g. "APR 3", "4:01 AM")
                    const datePattern = /^(JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)\\s+\\d+$|^\\d+:\\d+\\s*(AM|PM)$/i;
                    const date = lines.find(l => datePattern.test(l.trim())) || '';

                    results.push({ title, url, publication, date, teaser: description });
                }
                return results;
            }""")
        finally:
            page.close()
        return posts[:limit]

    finally:
        p.stop()


# --- LinkedIn ---

def get_linkedin_notifications(max_count: int = 20) -> list[dict]:
    """Fetch LinkedIn notifications.

    Returns list of notification dicts: text, time, url, unread.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        try:
            page.goto(
                "https://www.linkedin.com/notifications/",
                wait_until="networkidle",
                timeout=DEFAULT_TIMEOUT_MS,
            )
            page.wait_for_selector(".nt-card-list", timeout=DEFAULT_TIMEOUT_MS)

            notifications = page.evaluate("""() => {
                const cards = document.querySelectorAll('.nt-card');
                const results = [];
                for (const card of cards) {
                    const textEl = card.querySelector('.nt-card__text');
                    const timeEl = card.querySelector('time');
                    const linkEl = card.querySelector('a');
                    results.push({
                        text: textEl ? textEl.innerText.trim() : '',
                        time: timeEl ? timeEl.getAttribute('datetime') || timeEl.innerText.trim() : '',
                        url: linkEl ? linkEl.href : '',
                        unread: card.classList.contains('nt-card--new'),
                    });
                }
                return results;
            }""")
        finally:
            page.close()
        return notifications[:max_count]

    finally:
        p.stop()


def get_linkedin_messages(max_count: int = 10) -> list[dict]:
    """Fetch LinkedIn message threads.

    Returns list of thread dicts: sender, preview, time, url, unread.
    """
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.goto(
            "https://www.linkedin.com/messaging/",
            wait_until="networkidle",
            timeout=DEFAULT_TIMEOUT_MS,
        )
        page.wait_for_selector(".msg-conversations-container", timeout=DEFAULT_TIMEOUT_MS)

        messages = page.evaluate("""() => {
            const threads = document.querySelectorAll('.msg-conversation-listitem');
            const results = [];
            for (const t of threads) {
                const nameEl = t.querySelector('.msg-conversation-listitem__participant-names');
                const previewEl = t.querySelector('.msg-conversation-listitem__message-snippet');
                const timeEl = t.querySelector('time');
                const linkEl = t.querySelector('a');
                results.push({
                    sender: nameEl ? nameEl.innerText.trim() : '',
                    preview: previewEl ? previewEl.innerText.trim() : '',
                    time: timeEl ? timeEl.getAttribute('datetime') || timeEl.innerText.trim() : '',
                    url: linkEl ? linkEl.href : '',
                    unread: t.querySelector('.notification-badge') !== null,
                });
            }
            return results;
        }""")

        page.close()
        return messages[:max_count]

    finally:
        p.stop()


# --- Generic page content ---

def get_page_text(url: str, wait_selector: Optional[str] = None) -> str:
    """Fetch visible text content from a URL using the authenticated Chrome session."""
    p, browser, context = connect_with_retry()
    try:
        page = context.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_MS)
        if wait_selector:
            page.wait_for_selector(wait_selector, timeout=DEFAULT_TIMEOUT_MS)
        text = page.inner_text("body")
        page.close()
        return text
    finally:
        p.stop()


# --- Slack ---

# Slack DOM selectors for the web client.
# Slack's DOM uses stable data-* attributes alongside obfuscated class names.
# Prefer data-* selectors — they survive React re-renders and minor layout changes.
SLACK_SELECTORS = {
    "verified": "2026-03-26",
    # Message list container in a channel or DM
    "message_list": "[data-qa='message_container'], .c-virtual_list__scroll_container",
    # Individual message row
    "message": "[data-qa='message_container'] .c-message_kit__background, .c-message__body",
    # Message text body
    "message_body": "[data-qa='message-text'], .p-rich_text_block",
    # Sender name
    "sender": "[data-qa='message_sender_name'], .c-message__sender_button",
    # Timestamp link (title attr has readable time)
    "timestamp": "a.c-timestamp, [data-qa='timestamp']",
}


class SlackSelectorError(Exception):
    """Slack's DOM layout has changed — selectors in SLACK_SELECTORS need updating."""


def get_slack_dm_history(
    channel_id: str,
    bot_token: str,
    rob_user_id: str = "U06SHMT0TMG",
    limit: int = 100,
    oldest: Optional[str] = None,
) -> list[dict]:
    """Fetch Slack DM history via the Slack Web API (conversations.history).

    Uses the bot token from slack-config.json. Does not require Chrome.

    Args:
        channel_id: Slack channel or DM ID (e.g. D0AB1REU5MM).
        bot_token: Slack bot token (xoxb-...).
        rob_user_id: Slack user ID for Rob — messages from this ID are human turns.
        limit: Maximum number of raw messages to fetch (up to 200 per API call).
        oldest: Optional Unix timestamp string — only fetch messages after this time.

    Returns list of raw message dicts from the Slack API, newest-first.
    Each dict contains: ts, user, bot_id, text, subtype (if any).

    Raises RuntimeError on API error.
    """
    import urllib.request

    params = f"channel={channel_id}&limit={limit}"
    if oldest:
        params += f"&oldest={oldest}"
    url = f"https://slack.com/api/conversations.history?{params}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {bot_token}"})
    resp = urllib.request.urlopen(req, timeout=15)
    data = json.loads(resp.read())

    if not data.get("ok"):
        raise RuntimeError(f"Slack API error: {data.get('error', 'unknown')}")

    return data.get("messages", [])


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: cdp_helpers.py <command> [args]")
        print("Commands:")
        print("  check              - Check Chrome availability")
        print("  verify-gmail       - Verify Gmail selectors still work")
        print("  gmail              - Get inbox emails (JSON)")
        print("  gmail-search <q>   - Search Gmail")
        print("  calendar           - Get today's calendar events (JSON)")
        print("  substack           - Get Substack feed posts")
        print("  linkedin-notif     - Get LinkedIn notifications")
        print("  slack-dm <token> <channel_id>  - Get DM history (JSON)")
        sys.exit(1)

    command = sys.argv[1]

    if command == "check":
        available = is_chrome_available()
        print("available" if available else "unavailable")
        sys.exit(0 if available else 1)

    elif command == "verify-gmail":
        try:
            verify_gmail_selectors()
            print(f"Gmail selectors OK (verified {GMAIL_SELECTORS['verified']})")
        except GmailSelectorError as e:
            print(f"SELECTOR ERROR: {e}")
            sys.exit(1)

    elif command == "gmail":
        results = get_gmail_inbox()
        print(json.dumps(results, indent=2, default=str))

    elif command == "gmail-search" and len(sys.argv) > 2:
        results = search_gmail(sys.argv[2])
        print(json.dumps(results, indent=2, default=str))

    elif command == "calendar":
        results = get_calendar_events()
        print(json.dumps(results, indent=2, default=str))

    elif command == "substack":
        results = get_substack_posts()
        print(json.dumps(results, indent=2, default=str))

    elif command == "linkedin-notif":
        results = get_linkedin_notifications()
        print(json.dumps(results, indent=2, default=str))

    elif command == "slack-dm" and len(sys.argv) >= 4:
        results = get_slack_dm_history(channel_id=sys.argv[3], bot_token=sys.argv[2])
        print(json.dumps(results, indent=2, default=str))

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
