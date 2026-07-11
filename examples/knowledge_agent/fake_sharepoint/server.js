// Fake SharePoint knowledge base — stands in for an enterprise document library so an ODC AI agent
// can call it as a retrieval TOOL. Each document carries a DISTINCTIVE token (KESTREL-7, SQC-9,
// RVN-BLOCK7, GreenGate, PPAP Level 3) that a language model cannot know a priori — so if the agent's
// answer contains one, it PROVES the agent retrieved it through the tool rather than hallucinating.

const express = require("express");
const app = express();

// Log every inbound request so the Railway logs are an INDEPENDENT proof channel: when the ODC agent
// fires its retrieval tool, the resulting GET /search shows up here with its query string.
app.use((req, _res, next) => {
  console.log(`REQ ${req.method} ${req.originalUrl} ua="${req.headers["user-agent"] || ""}"`);
  next();
});

const DOCS = [
  {
    id: "SOP-ONB-001",
    title: "Supplier Onboarding Policy",
    site: "Supplier Quality",
    content:
      "Every new Rivian supplier must complete the KESTREL-7 conflict-minerals attestation within 14 " +
      "calendar days of intake. The sole approval authority for onboarding is the Supplier Quality " +
      "Council, internal routing code SQC-9. Onboarding cannot close until SQC-9 signs off.",
  },
  {
    id: "SOP-SCR-002",
    title: "Denied Party Screening SOP",
    site: "Compliance",
    content:
      "Denied-party screening runs each supplier name against the public OFAC SDN list AND Rivian's " +
      "proprietary internal blocklist, code RVN-BLOCK7. Any positive hit on RVN-BLOCK7 is an automatic " +
      "hard stop and must be escalated to the compliance review queue denyreview@rivian.example within 4 hours.",
  },
  {
    id: "SOP-PRT-003",
    title: "Part Release Checklist",
    site: "Manufacturing Engineering",
    content:
      "A supplier part may not be released to series production until it passes PPAP Level 3 and is " +
      "issued a GreenGate token by Manufacturing Engineering. No GreenGate token, no production release. " +
      "The GreenGate token is valid for 180 days and must be renewed before expiry.",
  },
  {
    id: "SOP-TIER-004",
    title: "Supplier Tiering Standard",
    site: "Supplier Quality",
    content:
      "Suppliers are tiered PLATINUM, GOLD, or STANDARD. PLATINUM requires an on-site audit score of at " +
      "least 92 and enrollment in the ZEPHYR-rated early-payment program. Tier is reviewed every 12 months.",
  },
];

function snippet(text, n) {
  return text.length > n ? text.slice(0, n) + "…" : text;
}

app.get("/health", (_req, res) => res.json({ ok: true, docs: DOCS.length }));

// List every document (title + site + id) — the "browse the library" view.
app.get("/documents", (_req, res) =>
  res.json(DOCS.map((d) => ({ id: d.id, title: d.title, site: d.site, snippet: snippet(d.content, 90) })))
);

app.get("/documents/:id", (req, res) => {
  const doc = DOCS.find((d) => d.id.toLowerCase() === req.params.id.toLowerCase());
  if (!doc) return res.status(404).json({ error: "not found" });
  res.json(doc);
});

// Keyword search across title + content — the retrieval tool the agent calls. Case-insensitive OR over
// whitespace-split query terms; returns whole documents so the agent can ground its answer in them.
app.get("/search", (req, res) => {
  const q = (req.query.q || "").toString().trim().toLowerCase();
  if (!q) return res.json({ query: "", count: DOCS.length, results: DOCS });
  const terms = q.split(/\s+/).filter(Boolean);
  const results = DOCS.filter((d) => {
    const hay = (d.title + " " + d.content + " " + d.site).toLowerCase();
    return terms.some((t) => hay.includes(t));
  });
  res.json({ query: q, count: results.length, results });
});

// Plain-text search — the retrieval tool the ODC agent calls. Returns the matching documents as one
// text/plain blob so the ODC consumed-REST method is a trivial `q -> Text` call (no nested JSON to map),
// and the text drops straight into the agent's prompt as grounding.
app.get("/searchtext", (req, res) => {
  const q = (req.query.q || "").toString().trim().toLowerCase();
  const terms = q.split(/\s+/).filter(Boolean);
  const hits = terms.length
    ? DOCS.filter((d) => {
        const hay = (d.title + " " + d.content + " " + d.site).toLowerCase();
        return terms.some((t) => hay.includes(t));
      })
    : DOCS;
  res.type("text/plain");
  if (!hits.length) return res.send("NO_RESULTS: no documents matched the query.");
  res.send(
    hits.map((d) => `### ${d.title} [${d.id}] (site: ${d.site})\n${d.content}`).join("\n\n")
  );
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => console.log(`fake-sharepoint listening on ${PORT}`));
