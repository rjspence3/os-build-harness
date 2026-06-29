# Home Banking — AI Agent Pipeline (Functional Spec Capture)

READ-ONLY introspection. Tenant `your-tenant.outsystems.dev`. Captured 2026-06-12 via
`context_agents` / `context_actions` / `app_refs` (no mutation, no publish).

All Home Banking agents + apps share **portfolioKey `f060491c-1aa9-4e19-941e-d38cd930b69a`**.

---

## 0. App constellation (canonical, non-sandbox/rebake set)

| App | assetKey | Type | Role |
|---|---|---|---|
| Home Banking Portal | `fa7ab595-f8cd-4140-8826-2acc484727b6` | WebApplication | Customer UI (apply, upload docs) |
| Home Banking Mobile | `03466756-800d-40d5-954a-394a99473f48` | MobileApplication | Customer mobile |
| Home Banking Backoffice | `555cac1f-af92-4461-9750-b635d6570495` | WebApplication | Officer UI — `requestdetail` shows agent responses + docs tab + history |
| **Home Banking Core** | `695efc5b-8f39-4a53-8d71-35c59097d245` | WebApplication | **System of record**: entities (HBLoanRequest, HBUpload, HBDocument, HBDocumentBinary, HAgentsResponse) + CRUD + public Service Actions |
| **Home Banking Loan Request** | `4b4c5f81-d528-41dd-a5a6-3d75367f74d3` | **Workflow** | **The orchestrator** — sequences the agents |
| AgentsCommonResources | `0d6e0ed8-79f8-42c2-a664-b4656db187eb` | eSpace | Shared agent infra (AgentsConsumerApp identity, AIMessage, AIAgentResponse) |

The agents are **standalone AIAgent apps** (each its own asset). They are NOT inside Core or the Workflow.
The same 4 agents are **multi-vertical/reusable** — each carries banking + insurance + procurement + eGov-permit
tool variants. Home Banking uses only the `HB*`/banking-labelled actions.

### `app_refs` proof of orchestration membership
`Home Banking Loan Request` (Workflow `4b4c5f81`) references exactly:
`HomeBankingCore`, `AgentsCommonResources`, `AppsCommonCore`, and the **4 agents**:
`IntakeAgent`, `EnrichmentAgent`, `UnderwriterAgent`, `CommunicationAgent`.
→ The pipeline is **Intake → Enrichment → Underwriter → Communication** (4 nodes, not 5).

`HomeBankingCore` (`695efc5b`) references only entity producers (AgentsCommonResources, FirebaseCloudMessaging,
System, AppsCommonCore, UltimatePDF, OutSystemsUI) — it holds data + CRUD, no agent calls.

---

## 1. Agent inventory (the 5 named agents)

The brainstorm named 5 (Intake, Enrichment, Underwriter, **OfferAgent**, Communicator). Reality: **4 agent apps**.
There is **no standalone OfferAgent** — the "offer" function is split between the **Underwriter** (produces the
decision/offer terms) and the **Communication** agent (`HBGenerateEmail` writes the approval email + offer-letter
reference). `DocumentValidationAgent` and `BankingAssistantAgent` exist in the tenant but are NOT referenced by the
loan-request Workflow (BankingAssistant = the standalone customer chat assistant; DocumentValidation = unused/aux).

Every agent is the **standard ODC AIAgent scaffold** with auto-generated actions:
`LoadMemory`, `BuildMessages`, `AgentTask`, `Call<Name>Agent` (public ServiceAction = entry point),
`StoreMemory`, `ClearMemory`, `NotifyBackofficeUI`, plus per-vertical `Get*GroundingData` (the **agent tools**) and
a `SaveAgentResponse`/`SaveResponse` (writes HAgentsResponse). System prompt / instruction lives on the
**AgentTask** node and is echoed into the **per-tool action descriptions** (the verb-described `Get*Data` actions —
this is how the model decides which tool to call).

### 1a. IntakeAgent — `8ac9d21b-0ce2-44a9-a787-6b1653f356c9` (rev 6)
- Desc: "analyze the document submitted and check if the information is valid and consistent across those documents… collect, organize, and initially validate all submitted information."
- **Entry**: `CallIntakeAgent` (ServiceAction, public) — in: RequestId, SessionId, AgentsConsumerAppId, LocaleId.
- **Tool / grounding**: `GetGroundingData` (`83606329…`) — in: RequestId, AgentsConsumerAppId;
  **out: `GroundingData` (Text) + `Documents` (DocumentStru List)**. ← **This is the agent that pulls the uploaded files into context.**
- I/O persist: `SaveResponse` (in: RequestId, `AIAgentResponse` struct) → HAgentsResponse.
- Aux: `GetFileFormat` (Filename → MIMEType), `NotifyBackofficeUI`.

### 1b. EnrichmentAgent — `bddf13e8-5c8c-4502-8c5c-caa42b59cd1a` (rev 9)
- **Entry**: `CallEnrichmentAgent` (ServiceAction, public).
- **Tools (verb-described, model-selected)** — multi-vertical:
  - `GetBankingData` (`9000319e…`): "act as an AI Banking Analyst for the Loan Request Application. Only answer based on context/extracted info from this request. don't use it for Insurance" — in: RequestId; out: Out_GroundingData. ← **HB tool.**
  - `GetInsuranceData`, `GetSupplierData`, `Get_eGovData` (other verticals).
- Extra HB-relevant: `SaveBasicCreditInfo` (FullCreditInfo, HBRequestId) — writes enriched credit data;
  `GenerateBuildingPermitData` / `GetMedicalInfo` / `GetPrescriptionInfo` (other-vertical fakers).
- Persist: `SaveAgentResponse` (RequestId, AIAgentResponse) and `SaveResponseAgent` (error path) → HAgentsResponse.

### 1c. UnderwriterAgent — `65e84055-6840-4722-868c-c48368cb4cbc` (rev 7)
- **Entry**: `CallUnderwriterAgent` (ServiceAction, public).
- **Tool**: `GetHBGroundingData` (`9881b0d7…`): "act as AI Loan Application Underwriting Agent. Only answer based on context/extracted info." — in: RequestId; out: GroundingData. (also Get_eGov / GetSupplier / GetInsurance grounding variants.)
- PII guard: **`AnonymizeData`** (in: CreditScore, AnnualIncome → CreditScoreAnon, AnnualIncomeAnon) — redacts PII before the LLM call.
- Persist: `SaveAgentResponse` (RequestId, AIAgentResponse) → HAgentsResponse.

### 1d. CommunicationAgent — `20420707-9d4b-4e15-b065-104870ae06c5` (rev 5) — "orchestrator of the final outcome"
- **Entry**: `CallCommunicatorAgent` (ServiceAction, public) — in: UserInput, SessionId, RequestId, UserId, IsCustomer, ToNotifyBO, IsDisregard, LocaleId, AgentsConsumerAppId; out: Response. (Richest signature — also the conversational endpoint.)
- **Tools**:
  - `HBGetDetailedGroundingDataForQA` (`bb837e2e…`): Q&A grounding; branches answer style on `IsCustomer` (conversational "you/your") vs Bank Officer (detailed). ← powers the backoffice/customer chat.
  - `HBGenerateEmail` (`7e8036f2…`): in LoanRequestId + EmailBody/Subject/ActionTitle prompts → GeneratedEmailBody. **Conditional on FinalDecision approved/rejected; on approve references the attached offer/confirmation letter.** ← the "Offer/Communicator" function.
  - `GetGroundingData` (general), plus Insurance/Supplier/Permit Q&A + email variants.
- Aux: `ClearAgentMemory`, `NotifyBackofficeUI`.

---

## 2. Orchestration (who sequences them)

The **`Home Banking Loan Request` Workflow app** (`4b4c5f81`) is the orchestrator. `context_actions` returns
**zero server actions** for it because its logic lives in **Workflow flow nodes**, not actions — it imports the 4
agents' public `Call*Agent` Service Actions and HomeBankingCore, and drives them in sequence on a submitted
`HBLoanRequest`. Progress is tracked in Core via `HBAgentsProgressSteps` / `IsEnrichmentAgentCompleted`; each
agent's output row is written to **`HAgentsResponse`** (Title, DataSummary, Description, AgentDecisionStatusId,
RecommendationId, RequestId) by that agent's own `SaveResponse`/`SaveAgentResponse` action.

**Sequence:** customer submits loan request + docs → Workflow runs
**Intake** (`CallIntakeAgent` — validates/organizes the uploaded docs; its `GetGroundingData` returns the
`Documents` list) → **Enrichment** (`CallEnrichmentAgent` → `GetBankingData`, pulls credit/banking analysis,
`SaveBasicCreditInfo`) → **Underwriter** (`CallUnderwriterAgent` → `GetHBGroundingData`, `AnonymizeData` then
decision) → **Communication** (`CallCommunicatorAgent` → `HBGenerateEmail` offer/decision email + powers Q&A chat).
Each writes a `HAgentsResponse` row + `NotifyBackofficeUI` so the backoffice `requestdetail` per-agent icons/history
update live.

**Which step reads the documents:** the **Intake** agent (`GetGroundingData` → `Documents` DocumentStru List) is
the first/primary doc reader; Enrichment then consumes the extracted/validated content via `GetBankingData`
grounding text (RequestId-scoped). Per the brainstorm note "Enrichment agent ingests the uploaded documents" the
doc content flows Intake-extract → Core → Enrichment-grounding.

---

## 3. Doc-upload flow (upload → store → agent-readable)

Customer UI (Portal/Mobile, `DocumentItem` block) uploads a file → HomeBankingCore public Service Actions:
- **`ServiceHBUploadCreate` / `ServiceHBUploadCreateOrUpdate`** (public ServiceAction) → server action
  `HBUploadCreate` / `HBUploadCreateOrUpdate` → **`HBUpload`** row, tied to the `LoanRequest` (`HBLoanRequest`).
- `HBUpload` materializes into **`HBDocument`** (metadata, typed by `HBDocumentType`) + **`HBDocumentBinary`** (bytes).
- Loan lifecycle: `ServiceLoanRequestCreate` / `LoanRequestCreate` + `ServiceRequestChangeStatus`/`RequestChangeStatus`
  move the request through statuses that the Workflow watches.
- Agent-readable path: Intake's `GetGroundingData` reads HBDocument/HBDocumentBinary (by RequestId) and returns the
  `Documents (DocumentStru List)` + grounding text into the AI model context. `GetFileFormat` maps filename→MIME so
  the model receives correctly-typed file parts.

Upload chain summary:
`file → ServiceHBUploadCreate → HBUploadCreate → HBUpload → HBDocument + HBDocumentBinary (HBDocumentType)`
`→ Intake.GetGroundingData(RequestId) → DocumentStru List → AI model grounding`.

---

## 4. "What it would take to clone this functionally via MCP"

### Authorable today (per memory + recipes 17-21, ODC MCP findings)
- **Entities + CRUD**: HBLoanRequest, HBUpload, HBDocument, HBDocumentBinary, HAgentsResponse, HBAgentType static
  records — entity creation + auto-actions (CreateAction/DeleteAll only — see `odc_mcp_entity_auto_actions_incomplete`)
  and hand-authored CRUD Server Actions are all MCP-authorable.
- **Public Service Actions** as the cross-app contract (the `Service*` wrappers, `Call*Agent` shape) — authorable
  (`CreateServiceAction`; library = ServerAction). Cross-app call works; in-app screen→ServiceAction needs a Server
  Action wrapper (`odc_mcp_screen_action_service_action_call`).
- **Agent internals**: Mentor MCP **can** author Agent internals (`odc_mcp_agent_app_authoring_wall` CORRECTED) —
  Call Agent element + AgentTask + tool wiring (the `actions` property = tool-wiring point,
  `odc_agent_tools_are_server_actions`). Grounding Server Actions (`Get*GroundingData` returning DocumentStru List)
  are normal Server Actions → authorable.
- **Doc handling**: file upload → binary entity → grounding action is standard entity/action work — authorable.
  `ServerRequestTimeout` 60s+ needed on every LLM-calling node (`odc_server_request_timeout`).

### Likely walls / risks (top 3)
1. **Agent system-prompt / AgentTask instruction authoring is the riskiest piece.** The "system prompt" lives in up
   to 3 places (AgentTask node instruction + per-tool action descriptions that drive tool selection + Call signature).
   MCP authoring of the AgentTask instruction text + binding the verb-described tools so the model actually selects
   them is unproven at this fidelity; the synthesis layer historically refuses introspection ("execute" framing) and
   agent-summary reads (`odc_mcp_session_context_wall`). **Verify against runtime, not chat** (`mentor_phantom_authoring`).
2. **Workflow authoring.** The orchestrator is a **Workflow app** (flow nodes, zero server actions) sequencing 4
   `Call*Agent` Service Actions + progress-step writes. ODC MCP workflow/flow-node authoring is the least-covered
   surface in the catalog — sequencing nodes, ConnectedBelow wiring, and watching request status are plausible
   (`odc_mcp_action_node_wiring`) but multi-agent Workflow orchestration end-to-end is a real unknown → biggest
   structural risk after the prompt.
3. **Multi-app reference graph + AgentsConsumerApp identity.** Functional parity needs Core ⇄ 4 agents ⇄ Workflow
   references plus the `AgentsConsumerAppId` identity threaded through every Call (`odc_agent_architectures` —
   AgentsConsumerApp Identifier is the multi-tenancy key). Reference-add is now MCP-tool-handled
   (`addReferenceToElements` + applyModelApiCode AddDependency) but the parallel/cascade cost and the consumer-app
   identity bootstrap are fiddly. Custom-PK publish crash (`osmcp_retest_canonical_reference`) is a latent scale risk
   if any entity uses a non-default PK.

**Net:** the data plane (entities, upload→binary→grounding, CRUD, Service Actions) and individual agent scaffolds
are MCP-authorable with high confidence. The two things that decide functional-parity success are (a) authoring the
**AgentTask instruction + tool-selection wiring** so an agent genuinely processes an uploaded doc, and (b) the
**Workflow that sequences the 4 agents**. Recommend a single-agent doc-processing proof first (Intake-only:
upload → HBUpload/HBDocumentBinary → GetGroundingData(DocumentStru) → AgentTask → HAgentsResponse) before attempting
the full 4-agent Workflow.
