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
2. Copy `.env.example` to `.env` and point `DATABASE_URL` at a Postgres
   database you can reach (a local Postgres instance, or a free
   [Neon](https://neon.tech) database work equally well). Set
   `SESSION_SECRET` to a random 32+ character string
   (`openssl rand -base64 32`).
3. Apply the schema:
   ```bash
   npx prisma migrate dev
   ```
4. Run the dev server:
   ```bash
   npm run dev
   ```

## Deploying to Vercel

1. **Create a Postgres database.** The simplest option is
   [Neon](https://neon.tech) (free tier, serverless Postgres) or
   [Vercel Postgres](https://vercel.com/docs/storage/vercel-postgres), which
   is Neon under the hood and can be provisioned directly from your Vercel
   project. Either way, copy the connection string it gives you.

2. **Import the repo on Vercel.** Go to
   [vercel.com/new](https://vercel.com/new), pick this repository, and set
   the project's **Root Directory** to `webapp` (this app lives alongside
   the existing `TOS-Billing-APP` QA test framework at the repo root, not at
   the top level).

3. **Set environment variables** on the Vercel project (Settings →
   Environment Variables):
   - `DATABASE_URL` — the Postgres connection string from step 1
   - `SESSION_SECRET` — a random 32+ character string

4. **Deploy.** Vercel runs `npm run build`, which does three things in
   order: `prisma generate` (builds the typed client), `prisma migrate
   deploy` (applies any pending migrations to the database in
   `DATABASE_URL`), then `next build`. So the database schema is created
   automatically on the very first deploy — no separate migration step
   needed.

5. Open the deployed URL. Sign in with any 10-digit mobile number; the app
   will show the one-time code on-screen (see **Auth** below) rather than
   texting it.

Every subsequent `git push` to the connected branch redeploys and re-runs
any new migrations automatically.

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
