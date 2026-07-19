# Neighborhood Event Signup — Specification

**Application**: Neighborhood Event Signup

---

## Part 1: Application Model

### Data Model

#### Entities

##### Event

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | Primary key |
| Status | EventStatus Id | Yes | Lifecycle state |
| Name | Text (200) | Yes | Event name |
| Description | Text (2000) | No | Long description |
| StartsAt | Date Time | Yes | Start time |
| Capacity | Integer | No | Maximum attendees |

##### Registration

| Attribute | Type | Required | Description |
|-----------|------|----------|-------------|
| Id | Auto Number | Yes | Primary key |
| EventId | Event Id | Yes | The event registered for |
| AttendeeEmail | Email | Yes | Registrant email |
| RegisteredOn | Date Time | Yes | Registration timestamp |

#### Static Entities

##### EventStatus

| Record | Label | Order |
|--------|-------|-------|
| Planned | Planned | 1 |
| Open | Open for Signup | 2 |
| Closed | Closed | 3 |
| Cancelled | Cancelled | 4 |

---

### Roles

#### Role Definitions

| Role | Description |
|------|-------------|
| **Resident** | Any authenticated user. Can browse events and register. |
| **Organizer** | Creates and manages events. |
| **Administrator** | Full access. |

---

## Part 2: Capabilities

The heart of this application is expressed as prose rather than tables, to exercise capability
extraction from narrative text.

**Browse and register for an event.** A resident opens the events list, which shows every event whose
status is Open for Signup. Selecting an event opens its detail, where the resident can register by
providing their email. Registration is refused once the event's capacity is reached, and the resident
receives a confirmation once their registration is recorded.

**Organize an event.** An organizer creates an event as Planned, sets its name, description, start
time, and capacity, then opens it for signup when ready. The organizer can view the list of
registrations for their event and close signups early. Cancelling an event notifies every registrant.

**Administer the system.** An administrator can manage all events regardless of organizer, and can
export the full registration list for any event to a spreadsheet for offline reporting.
