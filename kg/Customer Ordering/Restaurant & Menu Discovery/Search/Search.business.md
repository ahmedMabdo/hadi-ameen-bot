---
id: 8orders/customer-ordering/restaurant-and-menu-discovery/search-business
note_type: business
context: Customer Ordering
feature: Restaurant & Menu Discovery
last_updated: 2026-08-23
tags: [customer-ordering, restaurant-menu-discovery, business]
---
# Search

The home-page search bar — finds restaurants and menu items by name, ranks them, and decides which
ones are worth showing at all.

## What it is
When a customer types into the search box, the request doesn't go straight to the main order
database — it goes to Elasticsearch, a separate search-optimized database kept in sync with the
real one, so results can be ranked by relevance and tolerate typos instead of requiring an exact
match. Two layers work together: ordinary keyword matching (exact name, typo-tolerant fuzzy match,
"starts with"), and, for menu items, an optional AI-based "semantic" layer (Ollama running a model
called `nomic-embed-text`) that can match on meaning rather than exact spelling.

## Business rules (plain words)
- A restaurant-name match counts for more than a menu-item match when ranking who shows up first —
  searching "KFC" favors the restaurant named KFC over some other restaurant that merely sells a
  similar dish. This weighting is configurable (see the technical note and its canonical spec).
- Weak matches aren't just pushed to the bottom — they're dropped from the results entirely once
  their score falls below a percentage of the best match found for that search.
- Availability beats relevance for ordering: an open-and-not-busy merchant always outranks a busy or
  closed one, no matter how good the text match is. Only merchants in the same
  open/busy/closed group are then sorted by match quality.
- Results are limited to whatever delivery area the customer's current location falls into — not
  typed or selected, but derived from their coordinates.
- If a matched restaurant doesn't have enough matching items to look like a real result (fewer than
  5), the system tops up the list with other items from that restaurant's menu so it doesn't look
  empty.
- The AI/semantic matching layer only switches on for search text of 2 characters or more, and only
  when that whole search mode is enabled.
- **Known issue:** the AI/semantic layer that this feature is built around is turned on in every
  developer's own environment but turned off in production — so the search behavior nobody is
  actually testing against is the one customers use. Recorded in the knowledge graph's conflict log
  as a confirmed configuration divergence.
- **Known issue, high severity:** a recent change to how "out of stock" is calculated in search
  results has a confirmed bug — ordinary restaurant menu items (not grocery/mart items) can now
  incorrectly show as out of stock, because the flag now reads a stock-quantity field that was only
  ever meant to be tracked for mart items.
- **Known issue:** a customer can currently delete another customer's saved search-history entry —
  the delete action doesn't check who the history entry actually belongs to.
- **Known issue:** the admin "rebuild the search index" action requires no login at all to trigger —
  and, separately, currently does nothing when triggered (its actual rebuild logic is disabled),
  so today the bigger risk is the missing login check on an endpoint, not what it currently does.

## Who uses it
- **Roles:** Customers — the home-page search bar and (separately, not traced in this pass)
  in-restaurant item search. Admin — a "rebuild search index" action, currently a no-op (see above).
- **Screens:** Home page search bar and results, search filters/sorting, most-searched/recent-search
  suggestions.

## Related
- [[Restaurant.business|Restaurant]]
- [[MenuItem.business|Menu Item]]
- Technical detail: [[Search.technical|Search — technical]]
