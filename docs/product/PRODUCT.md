# Product context

> Agents read this at the start of every session (it is imported by `AGENTS.md`). Keep it under ~100 lines and current. Humans own this file.

## What it is
Verify My Client is a privacy-first client verification service for UK businesses that must check a client's identity before onboarding them. A business creates a verification request and sends the client a link. The client shares only the details the business asked for, for example "name and over 18" or "confirmed address". The business gets a verified result and an audit record for compliance, and never stores raw identity documents.

**This repository is a demo prototype. It uses synthetic data only, never real personal data.**

## Who uses it
- **Primary customers:** UK businesses with client identity-check obligations, such as solicitors, estate agents and accountants.
- **End users:** those businesses' clients, who receive a link and share the requested details.
- **Internal users:** none defined yet.

## Why it matters now
A demo prototype with no fixed deadlines. Favour clarity and correctness of the core flow over breadth.

## Core journeys
1. A business creates a verification request, choosing which details it needs.
2. The business sends the client a link to that request.
3. The client opens the link and shares only the requested details.
4. The business receives the verified result.
5. The business can view the audit record of the verification for compliance.

## Non-negotiables
- **Synthetic data only.** No real personal data in code, tests, fixtures, seeds, logs or screenshots.
- **Data minimisation.** Collect and disclose only the details the request asked for. Never return or keep more.
- **No raw identity documents are stored** on the business side. The business gets a result, not the documents.
- **A correct result matters more than speed.** A wrong "verified" or "not verified" harms the business or the client.
- **Every verification leaves an audit record.** Audit records never contain more personal data than the result itself.
- Never log personal details (names, dates of birth, addresses, document data).
- Built as if UK GDPR applies, even in the demo.

## Current priorities
1. Create a verification request and its client link.
2. The client shares only the requested details.
3. The audit record.

## Glossary
| Term | Meaning |
|---|---|
| UAT | User acceptance testing: a human checks the change works as intended |
| Business | The customer (e.g. a solicitor or estate agent) that requests a verification |
| Client | The business's client, the person being verified |
| Verification request | What a business creates: the details it needs from one client, plus the link sent to them |
| Requested details / claims | The specific facts asked for, e.g. name, over 18, confirmed address. Only these are shared |
| Verified result | What the business receives: which requested details were confirmed |
| Audit record | The compliance record of a verification (who requested what, when, and the outcome) |
| Synthetic data | Made-up test identities. The only data this demo may hold |
