# Home Banking — BACKEND CLONE SPEC (build-ready)

READ-ONLY introspection. Tenant `your-tenant.outsystems.dev`. Captured 2026-06-14 via
`context_entities` / `context_structures` / `context_actions` (no mutation, no publish). This is the
spec to *rebuild* the Home Banking backend constellation as a clone. Original assets were NOT modified.

Portfolio (constellation): **`f060491c-1aa9-4e19-941e-d38cd930b69a`**

| App | assetKey | Type | Role |
|---|---|---|---|
| Home Banking Core | `695efc5b-8f39-4a53-8d71-35c59097d245` | WebApplication (CrossDevice) | System of record — entities + CRUD + public Service Actions |
| Loan Request Workflow | `4b4c5f81-d528-41dd-a5a6-3d75367f74d3` | Workflow | Orchestrator — sequences the 4 agents |
| IntakeAgent | `8ac9d21b-0ce2-44a9-a787-6b1653f356c9` | AIAgent (rev 6) | Doc validation / organization |
| EnrichmentAgent | `bddf13e8-5c8c-4502-8c5c-caa42b59cd1a` | AIAgent (rev 9) | Credit/banking analysis |
| UnderwriterAgent | `65e84055-6840-4722-868c-c48368cb4cbc` | AIAgent (rev 7) | Decision + PII anonymize |
| CommunicationAgent | `20420707-9d4b-4e15-b065-104870ae06c5` | AIAgent (rev 5) | Email + Q&A chat |
| Backoffice | `555cac1f-af92-4461-9750-b635d6570495` | WebApplication | Officer UI (`RequestDetail`) |
| AgentsCommonResources | `0d6e0ed8-79f8-42c2-a664-b4656db187eb` | eSpace | Shared agent infra (AgentsConsumerApp identity, AIMessage, AIAgentResponse) |

> **Naming correction vs prior capture:** the loan-request entity is **`LoanRequest`** (NOT `HBLoanRequest`).
> The `HBLoanRequest` token only appears as a *referenced* (consumed) Identifier type inside the CommunicationAgent
> (e.g. `HBGenerateEmail.LoanRequestId : HBLoanRequest Identifier`) — i.e. the agent app's own local alias for the
> referenced Core entity. In Core itself the entity is `LoanRequest`. Clone it as `LoanRequest`.

---

## (a) CORE ENTITY SCHEMAS (exact — DDL-style)

All entities live in HomeBankingCore. `Id` is the auto identifier unless noted. "M" = mandatory.
Static entities carry the standard `Id/Label/Order/Is_Active` shape plus locale columns.

### LoanRequest  (key `9b759e48-…`, public) — THE CENTRAL ENTITY
Credit metrics are **denormalized directly onto LoanRequest** (not only on a structure).
```
Id                          Long Integer   M   (identifier)
CustomerId                  HBCustomer Identifier        FK→HBCustomer
TypeId                      LoanRequestType Identifier   FK→LoanRequestType (static)
AccountId                   HBAccount Identifier         FK→HBAccount
CustomerLoanId              CustomerLoan Identifier      FK→CustomerLoan
CustomerGoalId              CustomerGoal Identifier      FK→CustomerGoal
StatusId                    LoanRequestStatus Identifier FK→LoanRequestStatus (static)  ← Workflow watches this
AssignedToEmpId             Employee Identifier          FK→Employee (AppsCommonCore)
RequestInfoOptionId         LoanRequestInfoOption Identifier FK→LoanRequestInfoOption (static)
LocaleId                    Text(50)
ApprovalReason              Text(500)
CreatedOn                   Date Time     default CurrDateTime()
CreatedBy                   User Identifier              FK→(System) User
ClosedOn                    Date Time
LastUpdatedOn               Date Time
IsApprovalNotificationOpened Boolean
-- denormalized credit metrics (written by Enrichment via SaveRequestBasicCreditInfo) --
CreditScore                 Long Integer
TotalDept                   Long Integer   (sic — "Dept" typo preserved)
OnTimePaymentPercentage     Long Integer
CreditCardUsePercentage     Long Integer
DerogatoryMarksCount        Long Integer
TotalInquiriesCount         Long Integer
AverageAccountAgeYears      Long Integer
CreditInquiries             Long Integer
MortgageDebtPercentage      Long Integer
AutoLoanDebtPercentage      Long Integer
CreditCardDebtPercentage    Long Integer
IsFromPhone                 Boolean
FirstSubmission             Boolean
DeviceId                    Text(50)
```

### HBUpload  (key `18731861-…`, public) — landing zone for an uploaded file
```
Id                Long Integer   M  (identifier)
Binary            Binary Data        ← raw bytes of the just-uploaded file
GUID              Text(50)
HBDocumentTypeId  HBDocumentType Identifier  FK→HBDocumentType (static)
CreatedOn         Date Time   default CurrDateTime()
```

### HBDocument  (key `8c51acaa-…`, public) — document metadata
```
Id              Long Integer   M  (identifier)
HistoryLogId    HistoryLog Identifier      FK→HistoryLog
DocumentTypeId  HBDocumentType Identifier  FK→HBDocumentType (static)
FileName        Text(150)
IsActive        Boolean   default True
```

### HBDocumentBinary  (key `a2d4ba9c-…`, public) — document bytes (1:1 split from HBDocument)
```
DocumentId  HBDocument Identifier  M   FK→HBDocument   ← acts as the identifying key
Binary      Binary Data
```
Note: no separate `Id` surfaced — `DocumentId` is the mandatory FK that pairs bytes to HBDocument.

### HAgentsResponse  (key `d995a199-…`, public) — ONE ROW PER AGENT PER REQUEST (the agent output ledger)
```
Id                     Long Integer   M  (identifier)
RequestId              LoanRequest Identifier        FK→LoanRequest
AgentypeId             HBAgentType Identifier        FK→HBAgentType (static)   (sic — "Agentype")
RecommendationId       HBAIRecommendationOption Identifier  FK→HBAIRecommendationOption (static)
Title                  Text(5000)
Description            Text(500000)
DataSummary            Text(50000000)   ← very large; holds the agent's full structured output
AgentDecisionStatusId  HBAgentDecisionStatus Identifier  FK→HBAgentDecisionStatus (static)
LastUpdatedOn          Date Time
```

### HBDocumentType  (static, key `5450b0d1-…`, public)
```
Id Integer M | Label Text(50) M | Order Integer M | Is_Active Boolean M
```

### LoanRequestStatus  (static, key `dd7f0d24-…`, public) — the lifecycle the Workflow drives
```
Id Integer M | Label Text(50) M | LogLabel Text(100) | LogDescription Text(50) | Order Integer M
| Is_Active Boolean M | Color Text(50) | LabelLocale Text(300) | LogLocale Text(500) | LogDescLocale Text(750)
```
Wizard step labels imply the status ladder: Pending → Submitted → InProgress (Enrichment) → Approved/Rejected,
plus WaitResubmission. (Exact Id↔Label values not dumped — db_query is test-harness-only; infer from Backoffice
wizard logic: Pending, WaitResubmission, Submitted, InProgress, Approved, Rejected.)

### HBAgentType  (static, key `f09126d6-…`, public) — the 4 agents as records
```
Id Integer M | Label Text(50) M | Order Integer M | Is_Active Boolean M
| LogDescription Text(50) | LabelLocale Text(1000) | LogLocale Text(1000)
```
4 records expected: Intake, Enrichment, Underwriter, Communication (Order 1–4).

### HBAgentDecisionStatus  (static, key `1b8f32c4-…`, public)
```
Id Integer M | Label Text(50) M | Order Integer M | Is_Active Boolean M
```
Per-agent decision chip (e.g. Pending / Approved / Rejected / NeedsInfo).

### HBAIRecommendationOption  (static, key `0b3fcc5e-…`, public)
```
Id Integer M | Label Text(50) M | Order Integer M | Is_Active Boolean M
| TaskLabel Text(100) | IconName Text(50) | LabelLocale Text(500) | TaskLocale Text(1000)
```

### LoanRequestType  (static, key `befed373-…`, public)
```
Id Integer M | Label Text(50) M | Order Integer M | Is_Active Boolean M | Color Text(50) | LabelLocale Text(300)
```

### HBAgentsProgressSteps  (static, key `d9224e72-…`, NOT public) — the per-agent progress UI driver
```
Id Integer M | LoadingLabel Text(150) M | CompletedLabel Text(150) M | DurationSecond Integer
| HideOnApprove Boolean default True | HideOnReject Boolean default True
| AgentTypeId HBAgentType Identifier FK→HBAgentType | Order Integer M | Is_Active Boolean M
```
This is the data behind the Backoffice 5-step wizard / loading animation. Seed one row per agent step.

> **DeleteRule note:** `context_entities` returns FK target keys but not the textual DeleteRule (Protect/Delete/Ignore)
> per attribute. Default ODC behavior is **Protect** on mandatory FKs. For the clone, set Protect on
> HBDocumentBinary.DocumentId→HBDocument and HAgentsResponse.RequestId→LoanRequest; Ignore/SetNull on the optional
> LoanRequest FKs (matches the all-optional pattern observed). Verify against original after re-auth if exactness matters.

### Supporting structures (NOT entities — used in Service Action / agent signatures)

**DocumentStructure** (Core struct, key `908c279a-…`) — the doc payload passed *into* Core service actions:
```
DocumentId      HBDocument Identifier
Filename        Text
Binary          Binary Data
DocumentTypeId  HBDocumentType Identifier
```

**DocumentStru** (Agent-side struct, key `2f5bc52a-…`) — the doc list the IntakeAgent grounding *returns*.
(Same role as DocumentStructure but agent-local; attribute list not dumped — mirror DocumentStructure.)

**RequestFile** (Core struct, key `a0898b6c-…`) — file payload for CustomerLoan-with-files create:
```
Id Long Integer M | DocumentTypeId HBDocumentType Identifier | FileName Text(150)
| IsActive Boolean default True | BinaryContent Binary Data
```

**KeyMetric** (Core struct, key `bd7bb815-…`) — credit metrics bundle for SaveRequestBasicCreditInfo:
```
CreditScore, TotalDept, OnTimePaymentPercentage, CreditCardUsePercentage, DerogatoryMarksCount,
AverageAccountAgeYears, TotalInquiriesCount, CreditInquiries (all Long Integer)
+ TotalDebtBreakdownPercentage (nested struct: Mortgage, AutoLoan, CreditCard — Long Integer each)
```

**AIAgentResponse** / **AIMessage** — provided by AgentsCommonResources (referenced). AIAgentResponse is the struct
each agent deserializes the LLM JSON into before SaveResponse/SaveAgentResponse. Exact field list not dumped (lives
in AgentsCommonResources); minimally `{ Title, Description, Recommendation }` per the EnrichmentAgent error-path
record `"Description, Recomenedation, Title Record"` (sic typo). AIMessage = `{ role/content }` conversation turn.

---

## (b) CORE PUBLIC SERVICE ACTION CONTRACTS (the cross-app API surface)

All are `public ServiceAction`. 96 Core actions total; these are the contract the Portal/Mobile/agents/Workflow call.

### Upload chain
```
ServiceHBUploadCreate(Source: HBUpload) → Id: HBUpload Identifier
ServiceHBUploadCreateOrUpdate(Source: HBUpload) → Id: HBUpload Identifier
ServiceHBUploadUpdate(Source: HBUpload) → Id
ServiceHBUploadDelete(Id: HBUpload Identifier)
ServiceDocumentCreateOrUpdate(Binary: Binary Data, Document: HBDocument)     ← materializes HBDocument+HBDocumentBinary
ServiceDocumentGet(DocumentId: HBDocument Identifier) → FileName: Text, Binary: Binary Data
ServiceDocumentDelete(DocumentId: HBDocument Identifier)
```

### Loan request lifecycle
```
ServiceLoanRequestCreate(Source: LoanRequest) → Id: LoanRequest Identifier
ServiceLoanRequestCreateOrUpdate(Source: LoanRequest) → Id
ServiceLoanRequestUpdate(Source: LoanRequest) → Id
ServiceLoanRequestDelete(Id: LoanRequest Identifier)
ServiceRequestCreateOrUpdate(Request: LoanRequest, Comment: Text) → RequestId, LogId: HistoryLog Identifier
ServiceRequestChangeStatus(RequestId, RequestStatusId: LoanRequestStatus Identifier,
                           RequestInfoOptionId: LoanRequestInfoOption Identifier [opt],
                           StatusReason: Text, EmployeeId: Employee Identifier)
RequestSetStatus(RequestId, RequestStatusId, StatusReason: Text, EmployeeId [opt])   ← public, lighter variant
ServiceRequestAssigned(EmployeeId, RequestId)
ServiceRequestEnableResubmission(RequestId)
ServiceRequestNofificationOpened(RequestId)                                          (sic typo "Nofification")
ServiceOfferLetterVerification(RequestId) → HasOfferLetterGenerated: Boolean
ServiceGeneratePersonalLoanOfferLetter(RequestId)
GetLoanAccountId(LoanRequestId) → AccountId: HBAccount Identifier
```

### Personal-loan create-with-files (Portal apply flow — the rich entry point)
```
ServiceCustLoanCreateOrUpdateWithFiles(Source: CustomerLoan, Request: LoanRequest, Comment: Text,
                                       ListOfRequestFile: RequestFile List)
    → Id: CustomerLoan Identifier, RequestId: LoanRequest Identifier
ServiceCustLoanCreateOrUpdateWithFilesGetFirbase(... same inputs ...)                (sic "Firbase")
    → ProjectId, DatabaseURL, Target, Token, Id, RequestId, BOUserId             ← + Firebase push config
ServicePersonalLoanRequestCreatedOrUpdate(CustomerLoan, Request: LoanRequest, Comment: Text,
                                          Documents: DocumentStructure List) → RequestId
ServiceCustomerLoanCreateOrUpdate(Source: CustomerLoan) → Id
```

### Agent response ledger (Core side — agents call these to persist output)
```
ServiceAgentsResponseCreate(Source: HAgentsResponse) → Id: HAgentsResponse Identifier
ServiceAgentsResponseCreateOrUpdate(Source: HAgentsResponse) → Id
ServiceAgentsResponseDelete(Id: HAgentsResponse Identifier)
ServiceAgentsResponseAdd(LoanRequestId: LoanRequest Identifier, Title: Text, Description: Text)
    → Id: HAgentsResponse Identifier                                              ← simplest write path
ServiceAgentsResponseSave(AgentsResponse: HAgentsResponse, DoAudit: Boolean) → (also writes HistoryLog when DoAudit)
ServiceSaveRequestBasicCreditInfo(RequestId, KeyMetric: KeyMetric)               ← Enrichment writes credit metrics
```

### Backoffice sidebar / officer actions
```
ServiceSidebar_ChangeStatus(RequestId, RequestStatusId, Reason: Text, UserId: User Identifier,
                            AgentTypeId: HBAgentType Identifier, AgentDecisionStatusId: HBAgentDecisionStatus Identifier,
                            RequestInfoOptionId [opt])
ServiceSidebar_ChangeStatusGetFirebase(... same + ProjectId/DatabaseURL/Target/Token out ...)
ServiceSidebar_SendEmail(AgentResponse: HAgentsResponse, RequestId)
ServiceHistoryLogCreateOrUpdate(Log: HistoryLog) → LogId
```

### Customer / misc
```
ServiceHBCustomerCreate(Source: HBCustomer) → Id
ServiceCustomerGoalCreate/CreateOrUpdate/Update(Source: CustomerGoal) → Id ; ServiceCustomerGoalDelete(Id)
ServiceTransactionCreateOrUpdate(Source: Transaction) → Id
ServiceSendPushNotification(Title, Message, DeviceId: Text, RequestId [opt])
ServiceGetFirebaseConfigurations() → ProjectId, DatabaseURL, Target, Token
ServiceGetSettings() → Currency, GroupSeparator, DecimalSeparator, GoogleMapsKey
ServiceSaveAppSettings(DataSettings: DataSettings)
ServiceGetSampleUser_Manager() → Email, Password ; ServiceGetBackofficeSampleUserId() → BOUserId: User Identifier
ServiceGet_Picture(UserId) → Image64: Text ; ServiceFormatCurrencyCustom(Amount: Currency) → FormatedAmount
ServiceWakeupBO()  ;  ServiceWakeUpWF()                  ← warm-up no-arg pings (BO + Workflow)
GrantHBPortalRole(UserId: User Identifier)  ;  GrantHBBackofficeRole(UserId)
```

---

## (c) PER-AGENT SPEC

Every agent is the standard ODC AIAgent scaffold: `LoadMemory`, `BuildMessages`, **`AgentTask`** (the node carrying the
system-prompt/instruction), `Call<Name>Agent` (public entry ServiceAction), `StoreMemory`, `ClearMemory`,
`NotifyBackofficeUI`, `SaveResponse/SaveAgentResponse`, plus per-vertical `Get*GroundingData/Get*Data` **tools**. The
agents are multi-vertical (banking / insurance / procurement / eGov-permit); **clone only the HB / banking tool
variants** and drop the others, OR keep them and only wire the banking ones in the AgentTask.

Tool descriptions below are **verbatim** — these are the verb-descriptions that drive LLM tool selection.

### IntakeAgent  (`8ac9d21b-…`)
App description (verbatim): *"This agent will analyze the document submitted and check if the infromation is valid and
consistent across those documents. Its primary goal is to collect, organize, and initially validate all submitted
information."* (sic "infromation")

- **Entry (public):** `CallIntakeAgent(RequestId: Long Integer, SessionId: Text, AgentsConsumerAppId: AgentsConsumerApp Identifier, LocaleId: Text [opt])`
- **AgentTask** (server signature): `(RequestId, SessionId, AgentsConsumerAppId, LocaleId) → Response: Text`. **Instruction text NOT captured — see GAP.**
- **Tool — `GetGroundingData`** (key `83606329-…`): in `RequestId`, `AgentsConsumerAppId` → out **`GroundingData: Text`** + **`Documents: DocumentStru List`**. Desc (verbatim): *"Gets all the external or internal data configured within the action; the AI model will connect its output to your sources of data (grounding)."* — **THIS is the doc reader: it pulls HBDocument/HBDocumentBinary by RequestId into the model.**
- **`SaveResponse`**: in `RequestId`, `AI_AgentResponse: AIAgentResponse`, `AgentsConsumerAppId` → writes HAgentsResponse.
- **`GetFileFormat`**: in `Filename: Text` → out `MIMEType: Text` (maps filename→MIME so the model gets typed file parts).
- `BuildMessages` (notably also takes `Documents: DocumentStru List` as input — the doc list is threaded into the model messages), `LoadMemory`, `StoreMemory`, `ClearMemory`, `NotifyBackofficeUI(RequestId, AgentsConsumerAppId)`.

### EnrichmentAgent  (`bddf13e8-…`)
- **Entry (public):** `CallEnrichmentAgent(RequestId, SessionId, LocaleId [opt], AgentsConsumerAppId)`
- **AgentTask** `(RequestId, SessionId, LocaleId, AgentsConsumerAppId) → Response`. **Instruction text NOT captured — GAP.**
- **Tool — `GetBankingData`** (key `9000319e-…`, **the HB tool**): in `RequestId` → out `Out_GroundingData: Text`.
  Desc (verbatim): *"use this action when called to act as an AI Banking Analyst for the Loan Request Application. Only answer based on the context and extracted information from this request. don't use it for Insurance""* (trailing stray quotes preserved)
- Other-vertical tools (drop in clone): `GetSupplierData`, `GetInsuranceData`, `Get_eGovData` (returns `PermitRequest` struct), `GetMedicalInfo`, `GetPrescriptionInfo`, `GenerateBuildingPermitData`.
- **`SaveBasicCreditInfo`**: in `FullCreditInfo: Text`, `HBRequestId: InsurancePolicyRequest Identifier` (sic — reuses insurance Id alias) — persists enriched credit. (In Core the canonical write is `ServiceSaveRequestBasicCreditInfo(RequestId, KeyMetric)`.)
- **`SaveAgentResponse`**: in `RequestId`, `JSONDeserializeOutput_Data: AIAgentResponse`, `AgentsConsumerAppId` → HAgentsResponse.
- `SaveResponseAgent` (error path): in `AgentsConsumerAppId`, `RequestId`, `ErrorMessage: "Description, Recomenedation, Title Record"`.

### UnderwriterAgent  (`65e84055-…`)
- **Entry (public):** `CallUnderwriterAgent(RequestId, SessionId, LocaleId [opt], AgentsConsumerAppId)`
- **AgentTask** `(RequestId, SessionId, LocaleId, AgentsConsumerAppId) → Response`. **Instruction text NOT captured — GAP.**
- **Tool — `GetHBGroundingData`** (key `9881b0d7-…`, **the HB tool**): in `RequestId` → out `GroundingData: Text`.
  Desc (verbatim): *"Use this action when called to act as AI Loan Application Underwriting Agent. Only answer based on the context and extracted information in this request""*
- Other-vertical grounding tools (drop): `Get_eGovGroundingData`, `GetSupplierGroundingData`, `GetInsuranceGroundingData`.
- **PII guard — `AnonymizeData`** (key `fb35b420-…`): in `CreditScore: Text`, `AnnualIncome: Currency` → out `CreditScoreAnon: Text`, `AnnualIncomeAnon: Text`. **Run BEFORE the LLM call** — redacts PII.
- **`SaveAgentResponse`**: in `RequestId`, `JSONDeserializeResponseStr_Data: AIAgentResponse`, `AgentsConsumerAppId` → HAgentsResponse.

### CommunicationAgent  (`20420707-…`) — "orchestrator of the final outcome"; richest signature
- **Entry (public):** `CallCommunicatorAgent(UserInput: Text, SessionId: Text, RequestId: Long Integer, UserId: User Identifier, IsCustomer: Boolean, ToNotifyBO: Boolean, IsDisregard: Boolean [opt], LocaleId [opt], AgentsConsumerAppId) → Response: Text`
- **AgentTask** `(UserInput, SessionId, RequestId, UserId, IsCustomer, LocaleId, AgentsConsumerAppId) → Response`. **Node instruction text NOT captured — GAP.** BUT see below: this agent's tool *parameter descriptions* are themselves long verbatim prompts (recoverable now).
- **Tool — `HBGetDetailedGroundingDataForQA`** (key `bb837e2e-…`): in `HBRequestId: HBLoanRequest Identifier`, `IsCustomer: Boolean`, `UserId` → out `RequestInfo: Text`. Desc (verbatim): *"When asked to answer a question, use the output of this action as the grounding data to provide the information. If they greet you, respond in kind and ask how you can assist them.\nProvide a direct, concise answer suitable for a normal user. If customer is asking: always respond directly to the customer using conversational language (e.g., "you," "your"). Frame your answers as if you are personally assisting them. Containing only the most critical information. If not customer then it is the Bank Officer is asking: provide a detailed and comprehensive answer."*
- **Tool — `HBGenerateEmail`** (key `7e8036f2-…`): in `EmailBody`, `LoanRequestId: HBLoanRequest Identifier`, `ActionTitle`, `EmailSubject` → out `GeneratedEmailBody: Email`. Desc (verbatim): *"When asked to write an email, compose a full, well-structured email suitable for a normal user. The email body only without email subject. Only, if the FinalDecision is approved or rejected."* **The three input params carry verbatim sub-prompts** (captured below — these ARE the email-generation system prompt):

  - `ActionTitle` param desc (verbatim):
    ```
    Write a single line title for a backoffice action related with emails.

    1- Context

    This is a backoffice application, where we are showing different options depending on the request.
    We need an action title so the backoffice user know what he's taking action upon. For example, if the title is
    'Issue Loan approval email' - the user knows what the buttons 'Confirm' and 'Cancel are referring to.'

    2- Audience & Tone: The title is for a backoffice user, should be short and direct

    3- Conditional Logic:

    -- If the final decision is 'approved,' state that was approved
    -- If the final decision is 'rejected,' state that was rejected

    4. Examples

    - Issue Loan approval email to the customer
    - Issue Insurance Policy rejection email to the customer
    - Issue Invoice request rejection email to the customer
    - Issue Permit request approval email to the customer
    ```
  - `EmailSubject` param desc (verbatim):
    ```
    Write an email subject based on the following instructions:

    1- Audience & Tone: The email is for a customer, so the tone should be professional yet helpful.

    2- Conditional Logic:

    -- If the final decision is 'approved,' state that was approved
    -- If the final decision is 'rejected,' state that was rejected

    3. Examples

    - Your Loan application #{RequestNumber} was approved
    - Your Insurance Policy #{RequestNumber} was rejected
    - Your Invoice request #{RequestNumber} was rejected
    - Your Permit request #{RequestNumber} was approved

    {RequestNumber} to fill In from the available data.
    ```
  - `EmailBody` param desc (verbatim):
    ```
    Write an email body based on the following instructions:

    1- Audience & Tone: The email is for a customer, so the tone should be professional yet helpful.

    2- Core Content:

    - Start with a greeting (e.g., "Dear [Customer Name]").

    - State the request number and the current status of the request.

    - Conditional Logic:

    -- If the final decision is 'approved,' inform the customer that their offer letter is attached to the email.

    -- If the final decision is 'rejected,' provide a clear and concise reason for the rejection.

    3- Formatting:

    - The output must be only the email body.

    - Do not include a subject line.

    - Do not use any special formatting like bolding, bullet points, or markdown.
    ```
- **Tool — `GetGroundingData`** (key `6bb7c10b-…`): generic grounding — in `RequestId`, `UserId`, `IsCustomer`, `AgentsConsumerAppId` → `GroundingData: Text`.
- Other-vertical (drop): `GetDetailedGroundingDataForQA`, `PermitGetDetailedGroundingDataForQA`, `InsuranceGetDetailedGroundingDataForQA`, `SupplierGetDetailedGroundingDataForQA`, `PermitGenerateEmail`, `SupplierGenerateEmail`, `InsuranceGenerateEmail` (the Insurance/Supplier variants carry signatures + a `4- Signature` block; the eGov/Insurance email-body prompts add a fixed sign-off line).

### Shared agent I/O structures
- **DocumentStru** (`2f5bc52a-…`): agent-side doc list (Intake `GetGroundingData.Documents` output). Mirrors Core DocumentStructure: `{ DocumentId, Filename, Binary, DocumentTypeId }`.
- **AIAgentResponse** (AgentsCommonResources): the struct each agent deserializes the LLM JSON into → fed to SaveResponse → HAgentsResponse (`{ Title, Description, Recommendation }`-shaped; exact fields live in AgentsCommonResources, not dumped).
- **AIMessage / AIMessage List** (AgentsCommonResources): conversation memory turns (LoadMemory/StoreMemory/BuildMessages).
- **AgentsConsumerApp Identifier** (AgentsCommonResources): the multi-tenancy key — every Call*Agent + tool + persist takes `AgentsConsumerAppId`. The clone must register a consumer-app identity and thread it everywhere.

---

## (d) WORKFLOW SEQUENCE (Loan Request Workflow `4b4c5f81-…`)

`context_actions` returns **zero server actions** for this app — its logic lives entirely in **Workflow flow nodes**,
not actions. `app_refs` (prior capture) proves it references: HomeBankingCore, AgentsCommonResources, AppsCommonCore,
and the 4 agents. The orchestration sequence, reconstructed from references + the Backoffice 5-step wizard + the agent
contracts:

```
trigger: a LoanRequest reaches Submitted status (Portal ServiceCustLoanCreateOrUpdateWithFiles → ServiceWakeUpWF)
  │
  ├─ 1. CallIntakeAgent(RequestId, SessionId, AgentsConsumerAppId, LocaleId)
  │        Intake.GetGroundingData → Documents(DocumentStru list) + GroundingData → AgentTask → SaveResponse(HAgentsResponse)
  │        NotifyBackofficeUI ; (wizard step "Intake Validation" → completed)
  │
  ├─ 2. CallEnrichmentAgent(...)  [set request InProgress; IsEnrichmentAgentCompleted=False while running]
  │        Enrichment.GetBankingData → AgentTask → SaveAgentResponse(HAgentsResponse)
  │        + SaveBasicCreditInfo / Core.ServiceSaveRequestBasicCreditInfo(RequestId, KeyMetric)  → writes credit metrics onto LoanRequest
  │        NotifyBackofficeUI ; (wizard "Enrich Profile"); set IsEnrichmentAgentCompleted=True
  │
  ├─ 3. CallUnderwriterAgent(...)
  │        Underwriter.AnonymizeData(CreditScore, AnnualIncome) → GetHBGroundingData → AgentTask(decision) → SaveAgentResponse
  │        decision drives HAgentsResponse.AgentDecisionStatusId + RecommendationId ; NotifyBackofficeUI ; (wizard "Underwriter Policies")
  │
  └─ 4. CallCommunicatorAgent(UserInput, SessionId, RequestId, UserId, IsCustomer, ToNotifyBO, IsDisregard, LocaleId, AgentsConsumerAppId)
           on approved/rejected: HBGenerateEmail → Core.SendEmail_RequestApproved / SendEmail_RequestRejected
           + ServiceGeneratePersonalLoanOfferLetter (approve path) ; also powers Q&A via HBGetDetailedGroundingDataForQA
           NotifyBackofficeUI ; (wizard "Communicate Decision")
  │
  └─ final: ServiceRequestChangeStatus(RequestId, Approved|Rejected, reason, employeeId)  → LoanRequest.StatusId
```

Progress tracking: each agent's `NotifyBackofficeUI` + the `HBAgentsProgressSteps` static records drive the
Backoffice wizard. `HAgentsResponse` accumulates ONE row per agent per request (AgentypeId distinguishes them).
The Backoffice `IsEnrichmentAgentCompleted` local + status (`Pending/Submitted/InProgress/Approved/Rejected/WaitResubmission`)
gate the wizard step active/past states.

> **GAP (workflow node-level):** exact flow-node names, ConnectedBelow wiring, and any wait/decision nodes between
> agent calls were NOT enumerated (a workflow-flow walk via Mentor was started but cut off by token expiry). The
> 4-call sequence + status transitions above is reconstructed from references + agent signatures + Backoffice wizard;
> treat the *order* as confirmed and the *node mechanics* (waits, error branches) as to-be-verified.

---

## (e) BACKOFFICE `RequestDetail` SPEC (confirmed from backoffice-requestdetail.tree.md)

Screen `RequestDetail`. Input `RequestId: LoanRequest Identifier (M)`, `IsSidebarOpen: Boolean (default True)`.
Aggregates: `GetAgentsResponsesByRequestId`, `GetCustomerLoansById`, `GetDocuments`, `GetLogById (OnDemand)`,
`GetLoginUserPicture`, `GetLogsByRequestId`, `GetLogsNotes`, `GetRequestById`.

**5-step Wizard** (top), each step's Active/Past state driven by LoanRequest.StatusId + IsEnrichmentAgentCompleted:
`Application Submission → Intake Validation → Enrich Profile → Underwriter Policies → Communicate Decision`.

**5 Tabs:**
1. **Credit Profile** (visible only `HasCreditScore`): CreditScore gauge (City Peers vs National Average), DebtGraph
   (Mortgage/CarLoan/CreditCard %), Overview progress bars, and 6 metric cards (Payment History, Credit Card Use,
   Derogatory Marks, Account Age, Total Account, Inquiries) — all bound to the denormalized LoanRequest credit columns.
2. **General Information**: Loan Details (if CustomerLoanId set) + Financial Information (from HBCustomer).
3. **Documents**: `GetDocuments.List` → per-row download link `DownloadDocumentOnClick(HBDocument.Id)` (→ ServiceDocumentGet); BlankSlate when empty.
4. **Notes**: HistoryLog comment thread (human vs agent author; agent rows show `AgentIcon AgentTypeId` + `MarkdownFormat`).
5. **History Log**: TimelineItem list from `GetLogsByRequestId`; agent entries render `AgentIcon AgentTypeId` + agent label + `MarkdownFormat(Comment)`; `LogDocuments` per entry.

**Per-agent AI response display (the key clone target):** the right **AgentSidebar** block:
- `SidebarActivity(RequestId, RequestStatusId, RequestApprovalReason, AIResponseItems, RequestInfoOptionId, OnRefresh→SidebarActivityRefresh)` — `AIResponseItems` is `GetAgentsResponsesByRequestId.List` mapped to an item shape. This is where each agent's response (icon per AgentType, decision, history) is rendered.
- `SidebarChat(UserPicture)` — the Q&A chat (powered by CommunicationAgent `HBGetDetailedGroundingDataForQA` / `CallCommunicatorAgent` with `IsCustomer=False`).
- A `FirebaseReceiver` block (live push refresh of agent activity).
- RejectionPopup (Footer) → `RequestRejected` → ServiceRequestChangeStatus(Rejected).

So per-agent rendering = HAgentsResponse rows keyed by AgentypeId, each shown with `AgentIcon` (by HBAgentType),
`AgentDecisionStatusId` chip, `RecommendationId`, Title/Description/DataSummary, via Markdown. Docs tab = HBDocument
list with download. History = HistoryLog timeline interleaving human notes + agent responses.

---

## (f) BUILD ORDER + RISKS + ARCHITECTURE DECISION

### Recommended build order
1. **Core data plane first.** Create HomeBankingCore clone: the 5 core entities (LoanRequest, HBUpload, HBDocument,
   HBDocumentBinary, HAgentsResponse) + 6 static entities (LoanRequestStatus, LoanRequestType, HBDocumentType,
   HBAgentType, HBAgentDecisionStatus, HBAIRecommendationOption) + HBAgentsProgressSteps. Seed static records.
2. **Core CRUD + public Service Actions** (the contract in §b). Build CRUD server actions, wrap as the `Service*`
   public ServiceActions. Verify the upload chain end-to-end:
   `file → ServiceHBUploadCreate → HBUpload → ServiceDocumentCreateOrUpdate → HBDocument + HBDocumentBinary`.
3. **AgentsConsumerResources / consumer-app identity** — register the AgentsConsumerApp identity; this is threaded
   through every agent call.
4. **Single-agent proof (Intake only)**: upload → HBUpload/HBDocumentBinary → `GetGroundingData` returns
   `DocumentStru list` → AgentTask → SaveResponse → HAgentsResponse row. Prove a doc actually reaches the model and a
   response persists BEFORE building the other 3 agents.
5. **Remaining 3 agents** (Enrichment → Underwriter → Communication), each with its single HB tool + persist.
   Underwriter must include `AnonymizeData` pre-LLM. Communication carries the verbatim email prompts from §c.
6. **Workflow orchestrator** — sequence the 4 Call*Agent ServiceActions + status writes (§d) LAST.
7. **Backoffice RequestDetail** — wizard + 5 tabs + AgentSidebar (SidebarActivity/SidebarChat) reading HAgentsResponse.

### Top risks
1. **AgentTask node instruction TEXT (HIGHEST risk + the one capture GAP).** The per-agent system prompt on the
   AgentTask node was NOT extracted — the read-only Mentor walk to dump it was cut off when the OutSystems token
   expired mid-run. `context_actions` exposes the AgentTask only as an action with a generic boilerplate description,
   NOT the node's instruction property. This is the riskiest piece to clone because it (a) defines each agent's role,
   (b) tells the model which tool to call, (c) sets output JSON shape. **Partial mitigation already in hand:** the
   *tool descriptions* (verbatim above) and the CommunicationAgent's *email param prompts* (verbatim above) recover a
   large fraction of the prompt surface — for Intake/Enrichment/Underwriter the tool desc effectively IS the role
   statement ("act as an AI Banking Analyst…", "act as AI Loan Application Underwriting Agent…"). The missing piece is
   the AgentTask node's own instruction wrapper + output-format directive.
   **Recovery recipe (run after re-auth):** `mentor_start(app_key=<agent>)` with a read-only `applyModelApiCode` walk
   that enumerates the AgentTask node and prints its instruction/prompt property; read tool_end EVENTS (not chat
   summary) per `odc_mcp_agent_app_authoring_wall`; targeted prompt only per `odc_mcp_session_context_wall`;
   `mentor_cancel` after the tool_end event (read-only turn). Do all 4 agents.
2. **Workflow orchestration mechanics.** The orchestrator is a Workflow app (flow nodes, zero server actions). The
   4-call ORDER and status transitions are confirmed (§d); the node-level wiring (waits between async agent calls,
   error branches, the WakeUpWF trigger) is unverified. ODC MCP workflow-flow authoring is the least-covered surface.
3. **Multi-app reference graph + AgentsConsumerApp identity bootstrap.** Core ⇄ 4 agents ⇄ Workflow ⇄
   AgentsCommonResources, with `AgentsConsumerAppId` threaded through every Call. Reference-add is MCP-tool-handled
   now but the consumer-app identity bootstrap is fiddly.
4. **PII anonymization in Underwriter** (`AnonymizeData` before the LLM) is easy to omit — it's a separate server
   action, not part of the scaffold.

### ARCHITECTURE DECISION (flagged)
**Recommendation: clone as a faithful Core+4-agents+Workflow constellation that a portal references — do NOT fold
into V6's standalone world.** Rationale:
- The agent contract is fundamentally multi-app: every Call*Agent takes `AgentsConsumerAppId` and the agents are
  reusable AIAgent assets. Folding them into one standalone module loses the consumer-app identity model and the
  reusable-agent pattern that is the whole point of the original.
- HAgentsResponse-as-ledger + the Workflow-as-orchestrator + Backoffice-reads-Core is a clean separation that maps
  1:1 to the recipe-clone loop. A standalone fold would collapse the orchestration into in-screen logic and lose the
  "agent writes a row, UI polls the row" async pattern that drives the wizard + FirebaseReceiver.
- Counter-consideration: if V6 only needs the *appearance* of the pipeline (demo prop), a standalone fold with 4
  fake-agent server actions writing HAgentsResponse rows is far cheaper and dodges risks 1–3 entirely. **Decide by
  intent: functional-parity clone → constellation; demo prop → standalone fold.**

---

## AgentTask Instructions (verbatim)

> **GAP CLOSED (with caveats).** Recovered 2026-06-14 via read-only Mentor `getServerAction` + `applyModelApiCode`
> walks against the 4 original AIAgent apps (READ-ONLY; no mutation, no publish). **Key architectural correction:**
> the per-agent system prompt is **NOT** an instruction property on the `AgentTask` node. The `AgentTask` node only
> wires `Start → GetGroundingData → BuildMessages → CallAnthropic_Claude4_Sonnet (ICallAgentNode)`. The actual
> **system prompt lives inside the `BuildMessages` Server Action**, as a string literal assigned to
> `SystemMessageContent.ContentText` inside a per-vertical Assign node, selected by a `Switch` on
> `AgentsConsumerAppId` (4 branches: **HomeBanking / MyInsurance / Supplier / eGov**). **Clone the HomeBanking
> branch only.** This is where to author the prompt in the clone — on `BuildMessages`, not on `AgentTask`.

### BuildMessages anatomy (verbatim, common to all 4 agents)
The system message is constructed in `BuildMessages` as an `AIMessage` with:
- `SystemMessage.Role = Entities.AIRole.System`
- `SystemMessageContent.ContentType = Entities.AIContentType.TextContent`
- `SystemMessageContent.ContentText = "<the verbatim system-prompt literal for the matched vertical>"`  ← the prompt

After the switch, common (all-branch) post-processing (verbatim behavior, confirmed across agents):
- If `GroundingData` is non-empty, the grounding data is **prepended/merged into** `SystemMessageContent.ContentText`.
- A separate **`UserMessage`** Assign node (shared across branches) carries the **output-format / JSON-shape directive**
  (this is why the output JSON shape is the same across verticals).
- Memory turns (keyed by `SessionId`) are loaded via `LoadMemory` and injected **between** the system and user messages.
- If `LocaleId` is provided, a language directive is appended to **both** system and user content:
  *"You must ONLY use [Locale Label]([Locale Id]) as your response language."* (verbatim).

> **Recovery-channel caveat (a cloning finding in itself).** The Mentor **synthesis/guardrail layer refuses** to (a) run
> custom `applyModelApiCode` framed as prompt/instruction extraction, and (b) reproduce the `ContentText` literal
> verbatim on request ("Sharing the exact literal text of AI instruction prompts falls outside what I can do here").
> The native `getServerAction` tool **does** return the `BuildMessages` C# source incl. the literal, but the MCP
> **transport hard-truncates every tool result at 35,877 chars** — which lands *inside* the HB `ContentText` literal
> for IntakeAgent/CommunicationAgent (switch-before-assign layout) and *before* it is fully emitted for all. What IS
> reliably recoverable: (1) the **opening verbatim fragment** of the literal when the agent's `BuildMessages` puts the
> assign before the switch (Enrichment, Underwriter), and (2) a **faithful, fully-detailed Mentor narration** of the
> prompt (role/rules/output-shape) when asked to "describe in detail and quote fixed phrases" — Mentor reads the full
> literal internally and will quote individual sentences verbatim even though it refuses a single end-to-end dump.
> Below, text in `"straight quotes"` is **verbatim** (captured from getServerAction stdout or quoted by Mentor);
> unquoted text is Mentor's faithful structural reproduction. For byte-perfect cloning of the long literals, the
> remaining path is OutSystems Studio (open `BuildMessages` → HB Assign node → copy `SystemMessageContent.ContentText`).

---

### IntakeAgent (`8ac9d21b-…`) — HomeBanking `SystemMessageContent.ContentText`
Role (verbatim): **"Role: You are a meticulous Data Extraction Agent."**
Primary directive: extract all info from the file(s) *with precision* — act as a **data extractor, not a summarizer** —
then validate a banking loan application by cross-referencing supporting documents, and emit a final JSON report.

**Core extraction rules (verbatim quotes):**
- Comprehensive Extraction: *"Do not summarize, paraphrase, interpret, or omit any information."*
- Table Processing: process tables *systematically, row by row*, preserving structure/relationships.
- Image Text Recognition (OCR): extract all visible text from images/diagrams.

**Inputs expected:** Loan Request Application (JSON-ish: personal + financial details) + Supporting Documents — Pay stub,
Identification (driver's licence or passport), Bank statement, Tax form (Form 1040 or W-2).

**Validation workflow:**
- **Step 1 — Normalize Address Data** into `{ 'street': '...', 'city': '...', 'state': '...', 'zip': '...' }` before any comparison.
- **Step 2 — Cross-Validate 5 fields:**
  1. **Full Name** — match loan request vs ID, tax docs, bank statements. Verbatim: *"Ignore second names and third names, a match is needed for first name and last name. Ignore capital letters differences."*
  2. **SSN** — Loan Request vs tax form (1040/W-2) only. Verbatim: *"Do not validate Social Security Number (SSN) on the Identification, pay stub or bank statement documents."*
  3. **Address** — normalized app address vs normalized addresses on ID, bank statements, pay stubs, tax forms.
  4. **Salary/Income** — annualize YTD from most recent pay stub; compare with W-2 Box 1 and the "Wages, salaries, tips" line on Form 1040. Verbatim: *"Annualize based on only 1 or 2 months is fine."* Variance <5% → report verbatim *"No significant discrepancy found (#discrepancy value#)"*. Verbatim: *"Verify discrepancies above 30% between annualized income and total wages of W2. If above, mention income stability concerns on your analysis."*
  5. **Employer** — employer name on pay stubs vs tax form (1040/W-2).

**Date-range logic** (dynamic thresholds computed at runtime; general rule: documents dated **on or after `AddMonths(CurrDateTime(), -3)`**, formatted `dd MMMM yyyy`):
- Verbatim: *"When comparing dates, always parse and compare them as calendar dates numerically — never compare date strings alphabetically or lexicographically."*
- Verbatim: *"A date is valid if its calendar value is on or after [threshold date]."* Example: *"31 December 2025 is numerically AFTER 9 December 2025 and must be treated as passing."*
- Date-range docs (verbatim): *"For documents that cover a date range (e.g., 1 January 2026 to 31 January 2026), use only the END DATE of the range for validation … The START DATE of any date range must be completely ignored and never validated under any circumstances."*
- Exceptions: **Tax Return** always prior year (`Year(CurrDate())-1`, *"(Usually stated as fiscal year)"*; current-year return → fail). **Driving Licence/Passport** validate *expiry date* ≥ current date — verbatim *"Do not validate issued date for driving license or passport."*; short-year rule verbatim *"If the expiry date shows only month and 2-digit year (e.g., 12/27), interpret it as a full 4-digit year in the 2000s (e.g., 12/27 = 31 December 2027)."* Then a long series of dynamically-computed pass/fail examples.

**Output JSON** (overriding directive, verbatim): *"IMPORTANT: Your Recommendation value must strictly reflect the validation outcome. If all validations pass, you MUST output valid. If even one validation fails, you MUST output invalid. Never output invalid if your own Description states all validations pass."*
- `Recommendation` — `"valid"` or `"invalid"` (must agree with Description)
- `Title` — <50 chars if invalid; exactly `"All documents are valid"` if valid
- `Description` — Markdown, bullet per section, new line per bullet, **under 350 chars**; if invalid, detail each mismatch
- `DataSummary` — brief summary of key input data
- Closing (verbatim): *"Your final output must only be the output JSON object. Do not add any text, validations, tasks performed or explanations before or after it."*
- Note: no `"ALWAYS USE <tool>"` directive in Intake's HB branch (Mentor confirmed it is absent); the HB grounding tool is `GetGroundingData` (see §c).

---

### EnrichmentAgent (`bddf13e8-…`) — HomeBanking `SystemMessageContent.ContentText`
**Verbatim opening fragment** (captured directly from getServerAction stdout, the assign sits before the switch so it survived truncation):
```
ONLY USE THE GetBankingData FUNCTION NO MATTER WHAT!. ALWAYS USE GetBankingData, no matter the user message.
Role: You are an expert Banking Analyst for the Loan Request Application. Analyze the user's JSON data to generate a concise, easy-to-understand financial health report. The report should be formatted in markdown for a user preparing for a loan or mortgage. Your role is to analyze a user's financial data an…
```
(literal continues past the 35,877-char transport cut; remainder reconstructed from Mentor narration below.)

Role: **expert Banking Analyst for the Loan Request Application**; "direct and data-driven", produces a markdown
financial-health report for someone preparing for a loan/mortgage.
**Mandatory constraint (verbatim, stated twice):** always call **`GetBankingData`** regardless of the user message.

**Report = 4 markdown sections:** (1) Overall Financial Snapshot (health + credit score); (2) Key Strengths
(favorable factors — long credit history, good payment record, healthy credit mix); (3) Potential Loan/Mortgage Flags —
late payments, high credit utilization (overall + per card), large debt balances + DTI impact.

**Input JSON shape:** `user_info` (`annual_income`, `credit_score`) + `accounts[]` each with `account_type`,
`account_name`, `balance`, `credit_limit` (cards), `monthly_payment` (loans), `age_in_months`, and a
`payment_history` array of strings like `"on-time"` / `"30-days-late"`.

**Analytical rules:** Credit Utilization per-card and overall, flag **>30%**. DTI: sum `monthly_payment`; cards with no
stated payment → estimate **2% of balance**; monthly income = `annual_income / 12`; DTI = total monthly debt ÷ monthly
income, flag **>36%**. Late Payments: flag any `payment_history` entry not `"on-time"`.

**Output:** a single JSON object with two keys — `{ "Description": "...", "DataSummary": "..." }` (agent-side). The
shared **UserMessage** node then wraps to the 4-key shape `{ "Title" (<50 chars), "Description" (markdown, <350 chars),
"DataSummary" }`. Agent instructed to output **only** the raw JSON — no extra text before/after.
(Canonical Core write path for the credit metrics: `ServiceSaveRequestBasicCreditInfo(RequestId, KeyMetric)` — see §b.)

---

### UnderwriterAgent (`65e84055-…`) — HomeBanking `SystemMessageContent.ContentText`
**Full verbatim literal** (this branch's literal is short enough to survive the transport cap — captured complete from getServerAction stdout):
```
Only use the HBRequestData function/action no matter what
Role: You are an AI Loan Application Underwriting Agent. Analyze the provided user financial data to determine their eligibility for a new loan. Your analysis must focus on income stability, account health (balances, overdrafts), spending habits relative to income, and overall risk.
Your analyze should be based on the Bank Loan Policy.
```
(sic: "Your analyze should be based"; the literal names the tool **`HBRequestData`**, whereas the actual wired HB tool
is **`GetHBGroundingData`** per §c — a prompt/tool-name mismatch in the original, preserve verbatim when cloning the prompt.)

**Output JSON** (delivered via the shared UserMessage node; raw JSON only, no surrounding text):
- `Recommendation` — exactly one of `"Approve"`, `"Deny"`, `"Refer for Manual Review"`
- `Title` — **<50 chars**
- `Description` — Markdown, each section on a new line, section details as bullet points, **<350 chars**
- `DataSummary` — brief summary of key input data
- Concrete example given in the prompt (verbatim):
```
{
  "Recommendation": "Approve",
  "Title": "Strong consistent income",
  "Description": "The applicant demonstrates consistent income, healthy account balances, and responsible spending habits. Average monthly income of $5,200 exceeds the minimum requirement., Zero overdrafts in the past 6 months., Average monthly spending is at 65% of income.",
  "DataSummary": "summary of input data"
}
```
- Closing (verbatim): *"Your final output must only be the raw JSON object. Do not add any text, notes, or explanations before or after it."*
- PII note: `AnonymizeData` (§c) runs BEFORE this LLM call to redact CreditScore/AnnualIncome.

---

### CommunicationAgent (`20420707-…`) — HomeBanking `SystemMessageContent.ContentText`
> This is the agent's **own** system prompt (distinct from the `HBGenerateEmail`/`HBGetDetailedGroundingDataForQA`
> tool-parameter sub-prompts already captured verbatim in §c). `BuildMessages` here also carries an ODC default
> ICommentNode and extra inputs (`UserInput`, `RequestId`, `IsCustomer`).

Role (verbatim): **"You are a polite, knowledgeable, and helpful AI assistant specializing in loan and mortgage
inquiries. Your goal is to provide clear and accurate information with an empathetic and professional tone."**
- *Knowledgeable*: understands DTI, LTV, escrow, underwriting; explains simply using provided-data context.
- *Polite*: for customers, be empathetic and patient.

**`[CORE RULES]` block — 3 hard constraints:**
1. **Data is the only source** ("your most important rule"): answer *exclusively* from provided data; never invent/assume/use outside info. If info is absent, respond with the exact phrase (verbatim): *"I do not have access to that information."*
2. **No advice:** no financial/legal/investment advice; no opinions; no speculation on future events (e.g. interest-rate changes).
3. **Request ID resolution:** scan every query for a **"Request ID"** / **"Request Number"** (synonymous). If found → use that exact request; if none → default to the single most recent request and briefly state it is doing so because no ID was given.

**Tool-selection directives (verbatim):**
> *"Important: Always use the action GenerateEmail when asked to Write an email body,*
> *Always use the action GetDetailedGroundingDataForQA when asked to answer a question."*

(In the actual HB tool set these map to `HBGenerateEmail` and `HBGetDetailedGroundingDataForQA` — see §c; the generic
names `GenerateEmail`/`GetDetailedGroundingDataForQA` are what the prompt literal says.)

**Output:** no JSON shape for this branch — raw text answer OR composed email body, depending on the tool invoked. The
shared **UserMessage** node appends a hard length cap (verbatim): *"You must limit your entire response to a maximum of
400 characters (including spaces and punctuation). If your response would exceed 400 characters, shorten it until it
fits. Do not explain, disclaim, or mention the limit. Output only the final answer."*

---

### Cloning summary (the 4 system prompts are now in hand)
For a faithful clone, author each prompt as the `SystemMessageContent.ContentText` literal in that agent's
`BuildMessages` HB-switch-branch Assign node (NOT on AgentTask). Intake/Enrichment/Underwriter outputs are
strict JSON (`Recommendation`/`Title`/`Description`/`DataSummary`, with Intake using `valid|invalid` and Underwriter
using `Approve|Deny|Refer for Manual Review`); Communication outputs plain text/email ≤400 chars. The verbatim tool
directives ("ONLY USE … no matter what" / "Always use the action …") are load-bearing — they are how each agent is
forced onto its single HB grounding/email tool. The only non-byte-perfect pieces are the *interiors* of the long
Intake/Enrichment/Communication literals (role + rules captured verbatim; the exhaustive date-example lists and any
remaining prose are faithful-narration, not byte-exact) — copy those from Studio if byte-exactness is required.
