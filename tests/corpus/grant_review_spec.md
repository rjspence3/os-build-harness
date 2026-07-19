# Community Grants Review — Application Specification

**Application**: Community Grants Review

---

## Part 1: Application Model

### Data Model

#### Entities

##### GrantApplication

The central entity tracking a funding request through review.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | System-generated primary key |
| Status | ApplicationStatus Id | Yes | Current lifecycle state |
| ProgramId | Program Id | No | Funding program the request targets |
| SubmittedBy | User Id | Yes | User who submitted the application |
| Title | Text (200) | Yes | Short title of the request |
| Abstract | Text (2000) | No | Free-text summary of the proposal |
| AmountRequested | Currency | Yes | Funding amount requested |
| SubmittedOn | Date Time | No | Timestamp of submission |
| ReferenceCode | Text (50) | Yes | Human-readable display identifier |

##### Program

Reference entity for funding programs.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | System-generated primary key |
| Name | Text (200) | Yes | Program name |
| Code | Text (50) | Yes | Short program code |

#### Static Entities

##### ApplicationStatus

Lifecycle states for a grant application.

| Record | Label | Order | Description |
|--------|-------|-------|-------------|
| Draft | Draft | 1 | Initial state |
| Submitted | Submitted | 2 | Submitted for review |
| UnderReview | Under Review | 3 | Being reviewed |
| Approved | Approved | 4 | Funded; terminal |
| Rejected | Rejected | 5 | Declined; terminal |

##### ReviewOutcome

Possible reviewer decisions.

| Record | Label |
|--------|-------|
| Recommend | Recommend |
| Decline | Decline |
| Revise | Request Revision |

---

### Roles

#### Role Definitions

| Role | Description |
|------|-------------|
| **Applicant** | Any authenticated user. Can create and submit grant applications. |
| **Reviewer** | Reviews submitted applications and records an outcome. |
| **Administrator** | Full access. Manages programs and all applications. |

#### Permissions Matrix

| Action | Applicant | Reviewer | Administrator |
|--------|:---------:|:--------:|:-------------:|
| Create application | Yes | Yes | Yes |
| Submit application | Yes | -- | Yes |
| Record review | -- | Yes | -- |
| Manage programs | -- | -- | Yes |

---

#### GrantApplicationCreate

**Purpose**: Creation form for a new grant application.

##### Data Table

| Field | Label | Input Type | Validation | Default / Source |
|-------|-------|-----------|------------|-----------------|
| programId | Program | Dropdown | — | Program list |
| title | Title | Text input | Required | — |
| abstract | Abstract | Multi-line text | — | Free-text |
| amountRequested | Amount Requested | Currency input | Required | — |
| decisionBy | Decision By | Date picker | — | — |
| status | Status | Read-only badge | — | "Draft" |

##### Actions

| Action | Visible When | Behavior |
|--------|-------------|----------|
| Save & Close | Always | Saves the application as Draft |
| Submit Application | Always | Submits for review |

---

## Part 2: Technical Reference

### External Integrations

The application integrates with a disbursement REST API to issue approved grant funds electronically.
Planners look up disbursement status through the consumed API; base URL and credentials are configured
per environment.

For migration of historical applications, the system supports an admin-only Excel import: legacy
application records exported to spreadsheet are imported in bulk, matched by ReferenceCode.

### Business Rules

**Transition rules:**

| From | To | Triggered By | Side Effects |
|------|----|-------------|--------------|
| (new) | Draft | Applicant creates an application | Creator gets edit access |
| Draft | Submitted | Applicant submits | Edit access extends to Reviewer |
| Submitted | Under Review | Reviewer opens the application | — |
| Under Review | Approved | Reviewer recommends and admin confirms | Funding recorded |
