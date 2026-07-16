# Wyandotte Maintenance Requests — Modernized Specification

**Application**: Wyandotte Maintenance Requests

---

## Part 1: Application Model

### Data Model

#### Entities

##### MaintenanceRequest

The central entity tracking maintenance work at the Wyandotte site.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | System-generated primary key |
| Status | RequestStatus Id | Yes | Current lifecycle state |
| BuildingId | Building Id | No | Reference to the building where work is needed |
| CreatedBy | User Id | Yes | User who created the request |
| Description | Text (2000) | No | Free-text description of the requested work |
| AdditionalInfo | Text (unlimited) | No | Rich-text supplementary details |
| DateCreated | Date | Yes | Date the request was created |
| DateAccepted | Date Time | No | Timestamp when the request was accepted |
| MOCRequired | Boolean | No | Whether a Management of Change review is required |
| RequestNumber | Text (50) | Yes | Auto-generated display identifier |

##### Building

Reference entity for Wyandotte site buildings.

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | System-generated primary key |
| BuildingName | Text (200) | Yes | Descriptive name of the building |
| BuildingNumber | Text (50) | Yes | Site building number code |

#### Static Entities

##### RequestStatus

Lifecycle states for maintenance requests.

| Record | Label | Order | Description |
|--------|-------|-------|-------------|
| Draft | Draft | 1 | Initial state |
| Submitted | Submitted | 2 | Submitted for review |
| HoldForInformation | Hold for Information | 3 | Awaiting more info |
| Accepted | Accepted | 4 | Planner accepted |
| Closed | Closed | 5 | Work complete; terminal |
| Cancelled | Cancelled | 6 | Cancelled; terminal |

##### RequestType

Categories of maintenance work.

| Record | Label |
|--------|-------|
| Repair | Repair |
| Modification | Modification |
| NewInstallation | New Installation |
| ExpenseProject | Expense Project |
| NonMaintenanceSupport | Non-Maintenance Support |

---

### Roles

#### Role Definitions

| Role | Description |
|------|-------------|
| **Requester** | Any authenticated user. Can create maintenance requests and submit them. |
| **Maintenance Planner** | Reviews submitted requests and can accept or request more information. |
| **Maintenance Scheduler** | Manages work scheduling and can close requests. |
| **Administrator** | Full system access. Can manage buildings, config, and all requests. |

#### Permissions Matrix

| Action | Requester | Maintenance Planner | Maintenance Scheduler | Administrator |
|--------|:---------:|:-------------------:|:---------------------:|:-------------:|
| Create request | Yes | Yes | Yes | Yes |
| Edit own draft | Yes | -- | -- | Yes |
| Submit request | Yes | -- | -- | Yes |
| View all requests | -- | Yes | Yes | Yes |
| Accept request | -- | Yes | -- | -- |
| Request more information | -- | Yes | -- | -- |
| Edit scheduling fields | -- | Yes | Yes | Yes |
| Manually close request | -- | Yes | Yes | Yes |

---

#### MaintenanceRequestCreate

**Purpose**: Streamlined creation form for new maintenance requests.

##### Data Table

| Field | Label | Input Type | Validation | Default / Source |
|-------|-------|-----------|------------|-----------------|
| requestType | Request Type | Dropdown | — | Repair · Modification · New Installation |
| dateNeeded | Date Needed | Date picker | — | — |
| description | Description | Multi-line text | — | — |
| MOCRequired | MOC Required | Radio group | — | Yes · No |
| status | Status | Read-only badge | — | "Draft" |
| locationDetails | Location Details | Text input | — | Free-text |
| dateContactAvailable | Contact Available | Date picker | — | — |
| ccleaderApproval | CC Leader Approval | User picker | — | — |

##### Actions

| Action | Visible When | Behavior |
|--------|-------------|----------|
| Save & Close | Always | Saves the request as Draft |
| Submit Request | Always | Submits the request |

---

## Part 2: Technical Reference

### External Integrations

The application integrates with SAP for notification and work order number assignment. Planners enter SAP notification numbers and work order numbers directly into the maintenance request record after looking them up in SAP. No automated SAP API call is required for the initial modernization phase — the integration is a manual data-entry step backed by the SAP PM (Plant Maintenance) module accessed through the SAP GUI.

For bulk data migration and batch import of legacy request data, the application supports an Excel batch import process. The legacy system's request history can be exported as spreadsheet files and imported into the new system via an admin-only Excel import feature.

### Business Rules

**Transition rules:**

| From | To | Triggered By | Side Effects |
|------|----|-------------|--------------|
| (new) | Draft | Any authenticated user creates a request | Creator and Admin get edit access |
| Draft | Submitted | Requester submits | Edit access extends to Maintenance Planner |
| Submitted | Accepted | Maintenance Planner clicks Accept | DateAccepted is recorded |
| Submitted | Hold for Information | Maintenance Planner requests more info | Email sent to creator |
