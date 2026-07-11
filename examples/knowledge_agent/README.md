# Knowledge Agent — live test of an ODC AI agent with an EXTERNAL retrieval tool

A worked, live-proven example: an ODC AI Agent (`KnowledgeAgent`) that answers questions by calling a
**tool** which retrieves documents from an **external "SharePoint" service** (a small Node app hosted on
Railway). It proves the harness `agent` recipe end-to-end for the hardest agent shape — **native
Action-calling where the tool is an outbound REST integration**, not a local action.

## The two proofs this pins

1. **The native tool loop actually fires.** The agent's answer contains facts (`KESTREL-7`, `SQC-9`,
   `RVN-BLOCK7`, `GreenGate`, `SOP-ONB-001`) that exist ONLY in the external service — the model cannot
   invent them, so a correct+cited answer proves retrieval happened.
2. **The call really left ODC.** The Railway access logs show the inbound request with user-agent
   `OutSystems-ODC-RestConsume/2.0` and an **LLM-composed** query string — independent, side-effect proof
   that the ODC runtime made the outbound call, driven by the model.

## Architecture

```
POST /KnowledgeAgent/rest/AgentAPI/ask?Question=...
      │
      ▼  AgentFlow: LoadMemory → GetGroundingData("") → BuildMessages → [Call Agent widget]
      │                                                                        │  native tool loop
      │                                                     bounded by Call Condition  LoopCount >= 5
      ▼                                                                        ▼
   answer  ◄──────────────────  grounded on returned docs  ◄──  SearchKnowledgeBase(Query) : Text
                                                                     │ (server action)
                                                                     ▼
                                              Consumed REST API  SharePointKB.SearchText  GET /searchtext?q=
                                                                     │  ua=OutSystems-ODC-RestConsume/2.0
                                                                     ▼
                                              Railway:  fake-sharepoint  (server.js — this folder)
```

The agent has **no local knowledge** (`GetGroundingData` returns `""`); every fact comes through the tool.

## The fake SharePoint (this folder)

`fake_sharepoint/server.js` — an Express app serving a small Rivian supplier-policy knowledge base. Each
document carries a **distinctive token** a language model can't know a priori (KESTREL-7, SQC-9,
RVN-BLOCK7, GreenGate, ZEPHYR), so the tokens are the retrieval proof. Endpoints:

- `GET /health` · `GET /documents` · `GET /documents/:id`
- `GET /search?q=` — JSON results
- `GET /searchtext?q=` — **text/plain** results (used by the agent tool: a scalar `q -> Text` call makes
  the ODC consumed-REST method trivial, no nested-JSON structure to map). Every request is logged as
  `REQ <method> <url> ua="..."` so the ODC calls are visible.

### Deploy to Railway
```bash
cd fake_sharepoint
railway init --name fake-sharepoint-kb
railway up --detach
railway domain            # -> https://fake-sharepoint-kb-production.up.railway.app
railway logs --service fake-sharepoint-kb   # watch the inbound tool calls
```

## The ODC side (built entirely via the Mentor MCP)

Two Mentor turns on a blank `app_create kind=AIAgent` app (`KnowledgeAgent`):

- **E1 — outbound integration:** a Consumed REST API `SharePointKB` (base = the Railway URL, `GET
  /searchtext?q=`, plain-text response), a wrapper server action `SearchKnowledgeBase(Query) -> Knowledge`,
  and a throwaway `KbTestAPI` REST to verify the integration independently of the agent. *Finding: Mentor
  authors an outbound Consumed REST to an arbitrary external base URL cleanly via the Model API.*
- **E2 — the agent:** the 6-action ABC boilerplate (`LoadMemory → GetGroundingData → BuildMessages →
  [Call Agent widget] → StoreMemory → CallKnowledgeAgent`) with `SearchKnowledgeBase` **attached as an
  Action-calling tool** (description + AI-filled `Query`), `EnableActionCalling = true`, and Call Condition
  **`LoopCount >= 5`**.

### The load-bearing detail: the Call Condition
The agent Call Condition is the **BREAK/STOP** condition (the loop continues while it is FALSE). It MUST be
expressed on the runtime's built-in **`LoopCount`** and be false at the start:

- ✅ `LoopCount >= 5` — `0 >= 5` is false on iteration 0, so the loop proceeds and the tool fires; breaks at 5.
- ❌ `IterationCount <= 5` on a custom static input — true at start (`0 <= 5`) → the loop breaks at **0 tool
  calls** (runtime: *"Action calling break condition met. Total calls count: 0"*, HTTP 500). Live-observed
  failure; the harness `agent` recipe now emits the `LoopCount >= N` form.

## Result (2026-07-11, env Development)

Q: *"What attestation must a new supplier complete during onboarding, within how many days, and who
approves onboarding?"* →

> **KESTREL-7 conflict-minerals attestation** [SOP-ONB-001], within **14 calendar days** [SOP-ONB-001],
> approved by the **Supplier Quality Council (SQC-9)** [SOP-ONB-001].

Railway logs for the same invocation (the model refined its query across the bounded loop):
```
REQ GET /searchtext?q=supplier onboarding attestation approval days      ua="OutSystems-ODC-RestConsume/2.0"
REQ GET /searchtext?q=new supplier onboarding attestation approval days  ua="OutSystems-ODC-RestConsume/2.0"
REQ GET /searchtext?q=supplier onboarding attestation days approval      ua="OutSystems-ODC-RestConsume/2.0"
```

Tool-only facts + cited doc IDs + ODC-RestConsume access logs = the agent genuinely retrieved from the
external service. Test passed.
