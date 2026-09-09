"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";

type Step = "mobile" | "code";

export default function LoginPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>("mobile");
  const [mobile, setMobile] = useState("");
  const [devOtp, setDevOtp] = useState("");
  const [code, setCode] = useState("");
  const [needsProfile, setNeedsProfile] = useState(false);
  const [name, setName] = useState("");
  const [role, setRole] = useState<"USER" | "APPROVER">("USER");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function sendOtp(mobileNumber: string) {
    const res = await fetch("/api/auth/otp/request", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mobile: mobileNumber }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error ?? "Could not send code");
    return data.devOtp as string;
  }

  async function requestOtp(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      setDevOtp(await sendOtp(mobile));
      setStep("code");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function resendOtp() {
    setError("");
    setBusy(true);
    try {
      setDevOtp(await sendOtp(mobile));
      setCode("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  async function verifyOtp(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch("/api/auth/otp/verify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mobile, code, name, role }),
      });
      const data = await res.json();
      if (res.status === 422 && data.newAccount) {
        setNeedsProfile(true);
        return;
      }
      if (!res.ok) throw new Error(data.error ?? "Could not verify code");
      router.push(data.user.role === "APPROVER" ? "/approver" : "/user");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex-1 flex items-center justify-center px-4 py-16">
      <div className="w-full max-w-sm">
        <p className="text-xs font-mono uppercase tracking-wider text-accent mb-2">Towers Online Services</p>
        <h1 className="text-2xl font-semibold tracking-tight mb-1">Sign in to TOS Billing</h1>
        <p className="text-sm text-foreground-soft mb-8">
          Maintenance payments, approvals, and refunds — one place for residents and the approver.
        </p>

        {step === "mobile" && (
          <form onSubmit={requestOtp} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">Mobile number</span>
              <input
                required
                inputMode="numeric"
                placeholder="98765 00001"
                value={mobile}
                onChange={(e) => setMobile(e.target.value)}
                className="rounded-lg border border-line bg-surface px-3 py-2.5 text-sm outline-none focus:border-accent"
              />
            </label>
            {error && <p className="text-sm text-danger">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-accent text-white text-sm font-medium py-2.5 disabled:opacity-60"
            >
              {busy ? "Sending code…" : "Send code"}
            </button>
          </form>
        )}

        {step === "code" && (
          <form onSubmit={verifyOtp} className="flex flex-col gap-4">
            <div className="rounded-lg bg-accent-soft border border-line px-3 py-2.5 text-sm">
              <p className="font-medium text-accent mb-0.5">Demo mode — no SMS is sent</p>
              <p className="text-foreground-soft">
                Your one-time code is <span className="font-mono font-semibold text-foreground">{devOtp}</span>
              </p>
            </div>
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">6-digit code</span>
              <input
                required
                inputMode="numeric"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value)}
                className="rounded-lg border border-line bg-surface px-3 py-2.5 text-sm tracking-widest outline-none focus:border-accent"
              />
            </label>

            {needsProfile && (
              <div className="flex flex-col gap-4 rounded-lg border border-line p-3">
                <p className="text-sm font-medium">First time here — set up your account</p>
                <label className="flex flex-col gap-1.5">
                  <span className="text-sm">Your name</span>
                  <input
                    required
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="rounded-lg border border-line bg-surface px-3 py-2 text-sm outline-none focus:border-accent"
                  />
                </label>
                <div className="flex gap-2">
                  {(["USER", "APPROVER"] as const).map((r) => (
                    <button
                      type="button"
                      key={r}
                      onClick={() => setRole(r)}
                      className={`flex-1 rounded-lg border px-3 py-2 text-sm ${
                        role === r ? "border-accent bg-accent-soft text-accent" : "border-line text-foreground-soft"
                      }`}
                    >
                      {r === "USER" ? "Resident" : "Approver"}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {error && <p className="text-sm text-danger">{error}</p>}
            <button
              type="submit"
              disabled={busy}
              className="rounded-lg bg-accent text-white text-sm font-medium py-2.5 disabled:opacity-60"
            >
              {busy ? "Verifying…" : needsProfile ? "Create account & sign in" : "Verify & sign in"}
            </button>
            <div className="flex items-center justify-between">
              <button
                type="button"
                onClick={resendOtp}
                disabled={busy}
                className="text-sm text-accent underline underline-offset-2 disabled:opacity-60"
              >
                Resend code
              </button>
              <button
                type="button"
                onClick={() => {
                  setStep("mobile");
                  setNeedsProfile(false);
                  setError("");
                }}
                className="text-sm text-foreground-soft underline underline-offset-2"
              >
                Use a different number
              </button>
            </div>
          </form>
        )}
      </div>
    </main>
  );
}
