---
id: 8orders/customer-ordering/support-and-chat/support-and-chat-business
note_type: business
context: Customer Ordering
feature: Support & Chat
group: Support-and-Chat
last_updated: 2026-08-23
tags: [flow, business]
---
# Support & Chat — How a Problem Reaches a Human

## What this process is

Everything that happens when a customer or a driver needs help: talking to their counterpart during
a delivery, talking to support (with an automated first line before a human joins), submitting a
complaint or suggestion, and everything behind the scenes that routes, hands off, reassigns and
eventually closes that conversation. Read this when someone asks "who saw this conversation" or "why
didn't my complaint get a reply."

## The steps, in plain words

1. **Customer and driver message each other during delivery.** Once an order is out for delivery, the
   app opens a direct line between the customer and their driver — only while the order is actually on
   the way.
2. **Customer opens a support conversation.** The app checks working hours for the customer's city,
   then usually greets the customer with an automated bot menu rather than connecting straight to a
   person (a company-wide setting controls this).
3. **The bot's menu.** Depending on what is turned on, the customer can browse FAQs, ask about an
   order's status, or ask for a person. An already-open order conversation may skip straight to
   order-status help.
4. **FAQ self-service.** The bot searches a small bilingual FAQ library and offers up to three matching
   questions. There's a cap on how many searches a customer gets before the bot offers a human instead.
5. **Handing off to a person.** Whether the customer asks directly, exhausts the FAQ search limit, or
   automated order-status help fails, the same handoff runs: an agent is assigned, the customer is told
   a person is joining, and the agent sees the whole conversation so far, bot messages included.
6. **Picking which agent.** The system prefers an agent the customer already talked to recently, then
   otherwise picks whichever eligible, available agent currently has the fewest open chats. The same
   logic assigns driver-support conversations.
7. **The ongoing conversation.** Customer messages are saved and delivered to the agent immediately;
   agent replies are saved and pushed to the customer as a notification. How quickly the first reply
   came in is tracked for reporting.
8. **An agent goes offline mid-conversation.** If an agent turns off availability for a channel while
   still holding open conversations, those are automatically handed to another available agent in the
   background — unless nobody else is available, in which case the conversation simply stays put.
9. **Driver-to-support works the same way, minus the bot.** A driver reaching support goes straight to
   a human agent; there is no automated menu on this side. No available agent means an error, not a
   bot placeholder.
10. **Ending the conversation.** Either side can end an active support conversation; its duration is
    recorded for reporting.
11. **Rating.** Once ended, the customer can optionally rate the conversation (a company-wide setting
    decides whether rating is offered at all).
12. **Complaints and suggestions.** Separately from live chat, anyone can submit a free-text complaint
    or suggestion for staff to review later — a one-way mailbox, not a conversation.
13. **Order complaints raised by staff.** Admin staff can separately log a formal complaint against a
    restaurant tied to a specific order, feeding that restaurant's performance scoring.

## Who is involved

- **Customer:** opens the delivery chat and/or support chat, talks to the bot first (usually),
  optionally escalates to a person, rates the conversation, or submits a complaint.
- **Driver:** opens the delivery chat with their assigned customer, and a separate, bot-free line to
  support.
- **Support agent:** receives assigned or handed-off conversations, sees the full history including
  bot messages, can end a conversation.
- **The bot:** the automated first line for customer support only, deciding when to step aside.
- **Admin/Ops:** review submitted complaints, log formal order complaints against restaurants, and
  manage which agents are available on which chat channel.

## What can go wrong (in business terms)

- **Already fixed:** a gap that let any customer generate a live chat token for a stranger's
  in-progress delivery — reading and even posting in someone else's driver conversation — has been
  closed.
- Several "end this conversation" and "rate this conversation" actions don't check that the caller
  actually owns that conversation, even though sibling actions clearly do — a determined logged-in
  user could end or rate someone else's support conversation.
- A driver can, in principle, read another driver's support chat history, because that lookup was
  never scoped to "this driver only." Marking messages as read has the same kind of gap.
- The general complaint/suggestion mailbox requires a login; the formal order-complaint tool staff use
  to flag a restaurant is not locked at all — anyone on the internet can create or edit these records,
  a real gap given it feeds restaurant scoring.
- Staff viewing the general complaint/suggestion list can hit a crash if a complaint references a
  customer record that no longer resolves cleanly.
- An older, unused version of the driver-delivery chat's message-saving logic still sits in the
  codebase; nothing calls it today.
- It is not confirmed whether the delivery app's own backend receives real-time delivery confirmations
  for the customer-driver chat, or only for its own driver-support channel.

## What the company should know

The routing and handoff logic — bot menus, agent assignment, stickiness, reassignment on agent
unavailability — is well built and consistent between the customer and driver support lines. The weak
points sit at the edges: a handful of forgotten "who owns this conversation" checks on specific actions
(ending, rating, reading), and one completely unlocked door on the staff side (the formal
order-complaint tool). None of this needs a redesign — these are targeted, nameable gaps.
