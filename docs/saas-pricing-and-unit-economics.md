# PddGenerator — SaaS pricing, unit economics, and discussion notes

**Document purpose:** Capture the product/commercial discussion (distribution readiness, subscriptions, payments) and provide a **worksheet** to finalize **unit economics**: average AI cost, storage, and processing time **per session**.

**Location:** `docs/saas-pricing-and-unit-economics.md`

**Last updated:** 2026-04-10

---

## 1. Conversation summary (context from prior discussion)

### 1.1 Product direction

- Goal: Position **PddGenerator** as a **portable, extensible, market-ready SaaS** (customer-deployable or centrally hosted).
- Technical themes already in motion:
  - **Job messaging:** `JobEnqueuePort`, `JobEnvelope`, config-driven backends (e.g. Celery, SQS, Azure Service Bus, GCP Pub/Sub), multi-queue mapping, producer tests, retry/observability conventions.
  - **Auth:** Password + optional **Google** (OAuth popup / access token path), **email verification**, **password reset** via SMTP, dedicated frontend routes (`/auth`, `/auth/register`, `/auth/forgot`, `/auth/reset-password`).
  - **Ops readiness:** Deployment, security hardening, observability (discussed as remaining work for “distribution ready”).

### 1.2 Commercial / GTM topics raised

- **Distribution readiness:** Beyond feature work — deployment, secrets, TLS, backups, monitoring, incident response, SLAs for enterprise.
- **Payments:** A **billing module** is **not** optional for true multi-tenant SaaS if you charge by subscription; typical stack is **Stripe Billing** (or Razorpay for India-heavy B2B) with webhooks, customer portal, and DB mapping of `user` → `subscription` → `plan`.
- **Pricing:** Move from ad-hoc quotes to a **published tier model** + **usage overage** where COGS are variable (AI tokens, storage, compute minutes).

### 1.3 What this doc does *not* assume

- Exact model names, token counts, or infrastructure costs — those must be **measured or estimated** using the worksheet in §3.

---

## 2. Subscription-based costing model (draft for customer-facing use)

Use **one primary currency** per market (e.g. **INR** for India, **USD** for global). Annual = ~**2 months free** (≈ **17% discount**) unless you prefer a different rule.

### 2.1 Suggested tiers (feature + limits)

| Tier | Who it’s for | Seats / projects (example) | Included usage (example) | Support |
|------|----------------|-----------------------------|---------------------------|---------|
| **Starter** | Individuals / pilots | 1 seat, up to N active sessions | AI “credits” / month, storage cap, fair-use concurrency | Community / email (best effort) |
| **Growth** | Small teams | 3–10 seats, team workspace | Higher credits, higher storage, priority queue | Email, next-business-day |
| **Enterprise** | Regulated / large teams | SSO, SCIM (future), dedicated support | Custom limits, private deployment option, SLA | Named CSM, SLA, audit assistance |

**Typical SaaS add-ons (optional):**

- **Overage:** per 1k AI tokens, per GB-month storage, per extra seat.
- **Professional services:** onboarding, custom integrations, private cloud setup.

### 2.2 Example price points — **India (INR / month)**

*Illustrative only — adjust to your positioning and COGS.*

| Tier | Monthly (INR) | Annual (INR, billed yearly) | Notes |
|------|----------------|------------------------------|--------|
| Starter | ₹2,499 – ₹4,999 | ₹24,990 – ₹49,990 | Entry pilot; tight limits |
| Growth | ₹9,999 – ₹19,999 | ₹99,990 – ₹1,99,990 | Default for SMB |
| Enterprise | Custom | Custom | Min commit + SLA |

### 2.3 Example price points — **US / global (USD / month)**

| Tier | Monthly (USD) | Annual (USD, billed yearly) |
|------|----------------|-------------------------------|
| Starter | $29 – $49 | $290 – $490 |
| Growth | $99 – $199 | $990 – $1,990 |
| Enterprise | Custom | Custom |

### 2.4 What to include in the public pricing page (checklist)

- **What’s included** in “AI usage” (which models, rate limits, peak concurrency).
- **Storage** included vs overage (per GB-month).
- **Fair use** for background jobs (screenshots, exports, queue time).
- **Data residency** (if relevant) and **uptime** target by tier.
- **Trial** length and whether a card is required.

---

## 3. Unit economics — finalize these three metrics

### 3.0 Canonical definition of “session” (product + engineering)

**One sentence:** A **session** is one persisted PDD workflow workspace — a single row in `draft_sessions` (UUID `id`) — including all diagrams, steps, meetings, artifacts, AI calls, and background jobs tied to that id until the row is deleted (or you introduce an explicit archived/inactive lifecycle).

**Shorter (pricing page):** “Session” = one PDD draft workspace (`draft_sessions.id`) and everything stored or executed under that id.

**Engineering alignment**

| Concept | Implementation |
|--------|------------------|
| Session primary key | `draft_sessions.id`, referenced as `session_id` on child tables (`artifacts`, `meetings`, `action_logs`, process entities, …). |
| LLM token usage (per model / skill) | Structured logs: `event: "llm.completion.usage"`, `session_id`, `skill_id`, `model`, `prompt_tokens`, `completion_tokens`, `total_tokens`. Emitted from the API “Ask this session” path (`SessionGroundedQASkill`) and from worker `OpenAICompatibleSkillClient` / `transcript_interpreter` HTTP client (worker runs with `bind_log_context(session_id=…)` so `session_id` is present in JSON logs). |
| Background job wall time | Celery tasks `draft_generation.run` and `screenshot_generation.run` log `duration_seconds` and `duration_ms` on successful completion, in addition to existing `task_started` / `task_completed` events (structured context includes `session_id`). Session rows still record `draft_generation_*` / `screenshot_generation_*` timestamps for product-level boundaries. |

### 3.1 Average AI cost per session

**Goal:** Expected variable cost from LLM providers attributable to one session.

**Approach A — from provider bills (best):**

1. For a sample window (e.g. 30 days), sum **provider cost** for AI calls tagged with `session_id`.
2. Divide by **session count** in the same window (same definition of “session”).

\[
\text{avg AI cost / session} = \frac{\sum \text{allocated AI cost}}{\#\text{sessions}}
\]

**Approach B — from tokens × price card (if logging is good):**

1. Per session, sum **input tokens** and **output tokens** (and cached tokens if applicable) per model.
2. Multiply by **$/1K tokens** from your provider’s price list (include batch/discount if you use them).

\[
\text{AI cost} \approx \sum_{\text{models}} \left( \frac{T^{in}_m}{1000} p^{in}_m + \frac{T^{out}_m}{1000} p^{out}_m \right)
\]

**Worksheet — fill with real numbers:**

| Metric | Pilot / estimate | Measured (date range) |
|--------|------------------|------------------------|
| Avg input tokens / session | | |
| Avg output tokens / session | | |
| Dominant model mix (%) | | |
| Blended $/1K (in/out) | | |
| **Avg AI cost / session** | | |

**If you don’t have token logging yet:** run **10–20 representative sessions** in staging with logging enabled and take the average (label as **confidence: low** until production data exists).

---

### 3.2 Average storage per session

**Goal:** Bytes (or GB) stored for artifacts tied to a session: uploads, exports, generated files, thumbnails — whatever your `StorageService` persists under `session_id`.

**Formula:**

\[
\text{avg storage / session} = \frac{\sum_{\text{sessions}} \text{bytes(session)}}{\#\text{sessions}}
\]

**How to measure:**

- **Filesystem / object storage:** aggregate size by `session_id` prefix/folder.
- **Database:** if you store sizes per artifact row, `SUM(size) GROUP BY session_id`, then average.

**Worksheet:**

| Metric | Value |
|--------|--------|
| Avg bytes / session | |
| Avg GB / session | |
| % sessions with large uploads (define “large”) | |
| Implied $/session at your cloud storage + egress assumptions | |

**COGS note:** Storage has **GB-month** cost; large exports also drive **egress** — for pricing, often charge **overage on storage** and cap **download bandwidth** or price **exports** separately.

---

### 3.3 Average processing time per session

**Goal:** Wall-clock or CPU time spent on **async work** (queue workers, screenshot pipeline, exports) **attributable to** a session.

**Clarify two numbers:**

1. **User-perceived latency:** p50/p95 time from “Run” → “Ready” (product metric).
2. **Backend compute time:** sum of worker job durations for that session (COGS for compute).

**Formula (compute COGS-oriented):**

\[
\text{avg processing time / session} = \frac{\sum \text{job durations attributed to session}}{\#\text{sessions}}
\]

**Worksheet:**

| Metric | p50 | p95 |
|--------|-----|-----|
| End-to-end “run” latency | | |
| Sum of worker CPU time / session | | |
| Queue wait time / session | | |

**COGS:**

\[
\text{compute $/session} \approx \frac{\text{avg CPU-seconds}}{3600} \times \text{\$/vCPU-hour} \;+\; \frac{\text{avg GB-seconds memory}}{3600} \times \text{\$/GB-hour}
\]

(Use your container sizing or cloud bill allocation.)

---

### 3.4 Roll-up: variable COGS per session (sanity check)

\[
\text{variable COGS / session} \approx \text{AI} + \text{storage (allocated)} + \text{compute} + \text{egress (if material)}
\]

**Rule of thumb for SaaS:** target **gross margin** after variable COGS (often **70–85%+** for software-heavy; lower if AI COGS is high — then you need **usage limits** or **overage pricing**).

---

## 4. Payments module (reminder — not implemented in code at time of writing)

For subscription SaaS, plan for:

- **Provider:** Stripe Billing (global) and/or **Razorpay** (India collections) depending on customers.
- **Backend:** webhook endpoints (signed), idempotent processing, subscription state in DB.
- **Frontend:** checkout, customer portal, invoices.
- **Governance:** tax/VAT/GST handling per your accountant.

---

## 5. Next steps to “finalize” numbers

1. **Define “session”** in one sentence and align engineering metrics to it.
2. **Add logging** for tokens (per model) and **job durations** with `session_id` if missing.
3. **Run a 2-week** sample on staging or production (sanitized) and fill §3 worksheets.
4. **Set tier limits** so p95 usage stays under target margin at published prices.

---

## 6. Additional conversation notes (AI rate standard and billing)

### 6.1 Is prompt/completion per-1k token pricing standard?

Yes. Using separate rates for:

- `PDD_GENERATOR_AI_PROMPT_USD_PER_1K_TOKENS` (input/prompt tokens)
- `PDD_GENERATOR_AI_COMPLETION_USD_PER_1K_TOKENS` (output/completion tokens)

is a common industry baseline for:

- internal COGS tracking,
- unit economics dashboards,
- early-stage usage-based billing estimates.

### 6.2 Where this baseline is enough vs not enough

This approach is usually enough for directional pricing and margin checks. It is not fully invoice-grade by itself because real provider billing can also include:

- cached-token rates,
- batch vs standard vs priority tiers,
- tool-call charges,
- model/version pricing changes over time,
- taxes, regional adjustments, and FX differences.

### 6.3 Practical recommendation

Keep the current per-1k prompt/completion method as the default estimator, and evolve to a versioned pricing catalog (model + tier + effective date) when moving to strict customer invoicing and financial reconciliation.

---

## 7. Changelog

| Date | Change |
|------|--------|
| 2026-04-10 | Initial doc: pricing draft + unit economics worksheet + conversation summary |
| 2026-04-10 | §3.0 canonical session definition + engineering table; LLM usage and Celery duration logging |
| 2026-04-10 | Added note: per-1k prompt/completion pricing is standard baseline; listed invoice-grade caveats |
