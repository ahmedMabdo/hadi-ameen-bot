---
id: 8orders/admin/catalog-and-content-administration/overview
title: Catalog & Content Administration — Overview
note_type: overview
context: Admin
feature: Catalog & Content Administration
audience: Business
last_updated: 2026-08-23
tags: [admin, catalog-and-content-administration, business]
---
# Catalog & Content Administration — Overview

## What is this? (for everyone)

Everything a customer sees in the app that a restaurant did not put there.

Three kinds of thing live here. **Classification** — the brands, food types, store types, grocery
categories, cooking-time bands and languages that organise the catalogue so a customer can browse and
search it. **Content** — the privacy policy, terms and conditions and FAQ. And **outbound messaging** —
the ads and banners on the home screen, and the notifications and campaigns sent to customers, along
with the "audiences" that decide who receives them.

It is the largest area of the back office by number of screens.

## The Feature at a Glance

| # | Step (Screen) | Who | Purpose |
|---|---|---|---|
| 1 | Brands, food types, store types | Commercial | How restaurants and items are classified |
| 2 | Grocery categories | Commercial | How Mart products are organised |
| 3 | Cooking-time bands | Operations | Preparation-time expectations |
| 4 | Languages | Operations | Which languages content exists in |
| 5 | Sliders and banners | Marketing | The home-screen carousel |
| 6 | Ads and ad cards | Marketing | Promotional placements, including slots merchants reserve |
| 7 | Audiences | Marketing | Which customers a campaign targets |
| 8 | Notifications | Marketing | Messages sent now |
| 9 | Scheduled campaigns | Marketing | Messages that repeat on a schedule |
| 10 | Privacy policy, terms, FAQ | Legal, support | Customer-facing text |

## Business Flow (plain language)

1. Commercial staff maintain the classification data, which is what makes browsing and search work.
2. Marketing decides what appears on the home screen — sliders, ads and reservable ad slots.
3. To send a message, marketing first defines an audience (for example "customers who ordered in the
   last 7 days"), then either sends immediately or sets up a repeating campaign.
4. Legal and support keep the policy and help text current.

## What a business reader must know

This is the area with the **most recorded problems in the back office**, and they cluster around
messaging. Four points, all recorded:

**Two screens in this area can be used without signing in at all.** One of them is the scheduled-campaign
screen. That means, as things stand, an unauthenticated party could create or change notifications sent
to the entire customer base — messages carrying 8Orders' branding. This is the single most serious item
in the feature and it is not theoretical: the screens have no sign-in requirement of any kind.

**Repeating campaigns fire on the wrong schedule.** A defect in how the repeat interval is read means
monthly campaigns fire roughly every second month and yearly ones roughly every third year. Any campaign
that has looked "unreliable" is worth checking against this.

**Audience targeting is wider than it says.** When an audience is defined as "exactly N days", the
system actually selects "N days or fewer". So campaigns have been reaching more customers than intended
— not fewer, which matters if anyone has been judging campaign performance on the assumed audience size.

**The merchant-facing ad-card list can return malformed entries**, which can break the merchant portal's
display of available slots.

Two smaller notes for planning: several classification screens exist in near-identical **singular and
plural pairs** (food type and food types, store type and store types), which is confusing on its own and
actively risky given how the back office matches screens to permissions; and permission coverage inside
this one feature ranges from fully protected (the ad-card screens) to no protection at all.

Register rows: #439 and #567 (screens with no sign-in requirement), #422 (campaign interval), #423
(audience filter), #437 (malformed ad-card list), #560 (roleless cooking-time screen).

## Key Concepts

- **Classification data** — brands, food types, store types, grocery categories: how the catalogue is
  organised for browsing and search.
- **Ad card** — a promotional slot merchants can reserve.
- **Audience** — a rule that selects which customers a campaign reaches.
- **Immediate vs scheduled** — a notification sent now, versus a campaign that repeats.
- **Content page** — privacy policy, terms, FAQ.

## Detailed Notes

- [[Admin/Catalog & Content Administration/_knowledge-graph|Technical Knowledge Graph]] — measured
  permission coverage per controller, the four messaging mechanisms, and every finding.
- [[Admin/Catalog & Content Administration/_scenarios|Scenario Catalog]] — what happens if…
- [[Mart-and-Reference-Entities|Mart & reference entities]] · [[Audiance|Audiance]] ·
  [[Customer Ordering/Marketing & Content/_overview|Marketing & Content]] — the customer-facing side.
