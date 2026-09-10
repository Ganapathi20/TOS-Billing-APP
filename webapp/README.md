# TOS Billing

A web app for Towers Online Services maintenance billing: residents submit a
payment (UPI ID or QR-code upload) with proof, the approver reviews and
approves/rejects it, and can issue a refund on an approved payment.

Built with Next.js 16 (App Router), Prisma + Postgres, and mobile/OTP
role-based login (Resident vs Approver). No external services are required
to run it — OTPs are shown on-screen in place of SMS (see **Auth** below).

## Stack

- **Next.js 16** (App Router, Turbopack) + Tailwind CSS 4
- **Prisma 5** + **Postgres** for persistence
- **jose** for signed, httpOnly session cookies (no third-party auth service)

## Local development

1. Install dependencies:
   ```bash
   npm install
   ```
2. Copy `.env.example` to `.env` and point `DATABASE_URL` **and**
   `DIRECT_URL` at a Postgres database you can reach — for local
   development against a plain (non-pooled) Postgres instance these are
   just the same connection string twice. Set `SESSION_SECRET` to a
   random 32+ character string (`openssl rand -base64 32`).
3. Apply the schema:
   ```bash
   npx prisma migrate dev
   ```
4. Run the dev server:
   ```bash
   npm run dev
   ```

## Deploying to Vercel

### 1. Import the project

Go to [vercel.com/new](https://vercel.com/new), pick this repository
(`TOS-Billing-APP`), and before the first deploy expand **Root Directory**
and set it to `webapp` — this app lives in a subfolder alongside the
existing QA test framework at the repo root, not at the top level. Leave
the framework preset on Next.js (Vercel detects it automatically once the
root directory is set).

You can deploy once here (it'll fail at the `prisma migrate deploy` step
without a database — that's expected) and come back to fix it, or finish
the database setup first and deploy once at the end. Either works.

### 2. Create the database

In your Vercel project, open the **Storage** tab → **Create Database** →
choose **Postgres** (this provisions a serverless Neon Postgres database;
if your dashboard instead shows a **Marketplace** with a separate **Neon**
listing, use that — same underlying product). Pick a region close to
where you expect most traffic, name it, and create it.

Vercel will ask which project(s) to connect the database to — select this
one. Connecting it automatically adds a handful of environment variables
to your project (Settings → Environment Variables), typically including
things like `DATABASE_URL`, `DATABASE_URL_UNPOOLED`, `POSTGRES_URL`,
`POSTGRES_URL_NON_POOLING`, `POSTGRES_PRISMA_URL`, plus individual
`PGHOST`/`PGUSER`/`PGPASSWORD`/`PGDATABASE` pieces. The exact set varies by
how Vercel/Neon names things at any given time — what matters is that two
of them are a **pooled** connection string and a **direct/unpooled** one.

### 3. Map them to what this app expects

This app's `prisma/schema.prisma` reads exactly two variables:

- `DATABASE_URL` — must be the **pooled** connection string (used by the
  running app; Vercel functions are serverless, so many short-lived
  invocations share this pool)
- `DIRECT_URL` — must be the **direct/unpooled** connection string (used
  only when running `prisma migrate deploy` during the build — schema
  migrations can misbehave through a transaction-mode pooler)

Open Settings → Environment Variables on the project, find the two
connection strings Vercel just added (look at the values — the pooled one
usually has `-pooler` in the hostname, or is named `..._PRISMA_URL` /
without `NON_POOLING`/`UNPOOLED` in the name; the direct one usually has
`NON_POOLING` or `UNPOOLED` in its name), and:

- Add a variable named exactly `DATABASE_URL` set to the pooled value (or
  confirm one already exists with the right value — the integration
  usually names its pooled variable `DATABASE_URL` already)
- Add a variable named exactly `DIRECT_URL` set to the direct/unpooled
  value

Apply both to **Production**, **Preview**, and **Development** environments.

### 4. Add the session secret

Still in Settings → Environment Variables, add:

- `SESSION_SECRET` — any random 32+ character string, e.g. the output of
  `openssl rand -base64 32` run locally

### 5. Deploy

Trigger a deploy (Deployments tab → **Redeploy**, or push a commit —
adding/changing env vars doesn't redeploy automatically). Vercel runs
`npm run build`, which does three things in order: `prisma generate`
(builds the typed client), `prisma migrate deploy` (applies the schema to
whatever `DIRECT_URL` points at), then `next build`. So the database
tables are created automatically on the very first successful deploy — no
separate migration step to run by hand.

Watch the build log for the `prisma migrate deploy` line — a database
connection problem shows up there (before `next build` even starts) as a
`P1001`/`P1003`-style Prisma error, which almost always means one of the
two URLs was pasted into the wrong variable or an env var wasn't applied
to the environment being built.

### 6. Verify

Open the deployed URL, go to `/login`, and sign in with any 10-digit
mobile number — the app shows the one-time code on-screen instead of
texting it (see **Auth** below). If sign-in works and you can submit a
payment, the database is wired up correctly.

Every subsequent `git push` to the connected branch redeploys and re-runs
any new migrations automatically.

## Testing without login

To click through the app without going through OTP sign-in each time, set
the `SKIP_AUTH` environment variable to `"true"` (locally in `.env`, or in
Vercel's Environment Variables + redeploy). With it set:

- Visiting the site lands you straight on the Resident dashboard, signed in
  as a seeded "Test Resident" account — no phone number needed.
- A **"Switch to Approver view"** / **"Switch to Resident view"** link
  appears next to Sign out, swapping between the two seeded test accounts
  (Test Resident and Test Approver) with one click — handy for testing the
  full submit → approve → refund loop back and forth.
- A yellow **TEST MODE** banner appears across the top as a reminder it's on.

**Turn it back off before anyone but you uses the app** — set `SKIP_AUTH`
back to `"false"` (or delete the variable) and redeploy. It's a real
authentication bypass: anyone who can reach the site while it's on can sign
in as either role with no verification at all. The route it relies on
(`/api/test/login`) returns a 404 by itself whenever the variable isn't
exactly `"true"`, so leaving it unset is safe by default.

## Auth

There's no SMS provider wired up, so `POST /api/auth/otp/request` returns
the generated code directly in the response (`devOtp`), and the login page
displays it under a "Demo mode" banner instead of sending a text. This
keeps the app deployable with zero paid dependencies. Before using this
somewhere real people rely on, replace `src/lib/otp.ts`'s `issueOtp` with a
real SMS provider (Twilio, MSG91, etc.) and stop returning `devOtp` from
the API.

The first time a mobile number signs in, it's asked for a name and a role
(Resident or Approver) and a `User` row is created; every sign-in after
that reuses the existing account and role.

## Data model

- `User` — mobile number, name, role (`USER` or `APPROVER`)
- `Otp` — short-lived one-time codes for sign-in
- `Transaction` — one submitted payment: amount, method (`UPI_ID` or
  `QR_UPLOAD`), the UPI ID or QR image, the uploaded proof image, computed
  convenience fee/total, status (`PENDING_APPROVAL` → `APPROVED`/`REJECTED`
  → optionally `REFUNDED`), and the approver's decision/refund proof.

Images (QR code, payment proof, refund proof) are uploaded as base64 data
URIs and stored directly on the `Transaction` row, capped at ~1.5MB each.
That's fine for a small society's transaction volume; for heavier use,
swap this for [Vercel Blob](https://vercel.com/docs/storage/vercel-blob) or
S3 and store a URL instead.

## Fee formula

`src/lib/charges.ts` computes an illustrative 2% + ₹3 convenience fee. It's
a placeholder — swap in the society's real fee schedule when you have it.

## Relationship to the existing test suite

The rest of this repository (`framework/`, `tests/`, `conftest.py`, ...) is
a separate Appium/Selenium QA harness that drives the native Android app
`com.towers.onlineservices` against a backend API. This `webapp/` directory
is unrelated to that harness — it's a standalone, deployable reference
implementation of the same UPI-ID / QR-upload / approve / refund flow the
tests describe, built so there's something real to deploy and to point
future backend work at.
