## REMOVED Requirements

### Requirement: Public participant list
**Reason**: Replaced by `public-entrants`, which lists the entrants per discipline on the tournament's own page. The hidden/greyed choice is dropped there: unpaid entrants are always shown faded, because hiding them left a queue standing behind seats that looked free.
**Migration**: The payment rules (confirmed only where Squire collects, the organizer's hand tick otherwise, an unticked entrant carrying no mark) move unchanged into `public-entrants` "The Paid column states only what Squire can stand behind". The as-of statement stays in `external-registration`. `GET /api/tournaments/{slug}/participants` is replaced by the per-discipline entrants endpoint, and `unpaid_list_treatment` is removed from the model, the API, Setup and the export document.
