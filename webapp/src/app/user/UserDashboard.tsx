"use client";

import { useEffect, useMemo, useState, FormEvent } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import { computeCharges } from "@/lib/charges";
import type { Transaction, PaymentMethod } from "@/lib/types";

function fileToDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function UserDashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);

  const [amount, setAmount] = useState("");
  const [method, setMethod] = useState<PaymentMethod>("UPI_ID");
  const [upiId, setUpiId] = useState("");
  const [qrImage, setQrImage] = useState("");
  const [proofImage, setProofImage] = useState("");
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const charges = useMemo(() => {
    const value = Number(amount);
    if (!Number.isFinite(value) || value <= 0) return null;
    return computeCharges(value);
  }, [amount]);

  async function loadTransactions() {
    const res = await fetch("/api/transactions");
    const data = await res.json();
    if (res.ok) setTransactions(data.transactions);
    setLoading(false);
  }

  useEffect(() => {
    let cancelled = false;
    fetch("/api/transactions")
      .then((r) => r.json())
      .then((data) => {
        if (!cancelled) setTransactions(data.transactions ?? []);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      const res = await fetch("/api/transactions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount: Number(amount), method, upiId, qrImage, proofImage, note }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not submit payment");
      setAmount("");
      setUpiId("");
      setQrImage("");
      setProofImage("");
      setNote("");
      await loadTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 flex flex-col gap-10">
      <section>
        <h2 className="text-lg font-semibold mb-1">Submit a maintenance payment</h2>
        <p className="text-sm text-foreground-soft mb-5">
          Pay via UPI ID or by scanning a QR code, then upload proof — your approver is notified automatically.
        </p>

        <form onSubmit={submit} className="flex flex-col gap-4 rounded-xl border border-line bg-surface p-5">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Amount (₹)</span>
            <input
              required
              type="number"
              min={1}
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
              className="rounded-lg border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </label>

          {charges && (
            <p className="text-xs text-foreground-soft font-mono">
              + ₹{charges.fee} convenience fee → total ₹{charges.total}
            </p>
          )}

          <div className="flex gap-2">
            {(["UPI_ID", "QR_UPLOAD"] as const).map((m) => (
              <button
                type="button"
                key={m}
                onClick={() => setMethod(m)}
                className={`flex-1 rounded-lg border px-3 py-2 text-sm ${
                  method === m ? "border-accent bg-accent-soft text-accent" : "border-line text-foreground-soft"
                }`}
              >
                {m === "UPI_ID" ? "Paid to UPI ID" : "Paid via QR code"}
              </button>
            ))}
          </div>

          {method === "UPI_ID" ? (
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">UPI ID you paid to</span>
              <input
                required
                placeholder="society@upi"
                value={upiId}
                onChange={(e) => setUpiId(e.target.value)}
                className="rounded-lg border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
              />
            </label>
          ) : (
            <label className="flex flex-col gap-1.5">
              <span className="text-sm font-medium">QR code you scanned</span>
              <input
                required
                type="file"
                accept="image/*"
                onChange={async (e) => {
                  const file = e.target.files?.[0];
                  if (file) setQrImage(await fileToDataUri(file));
                }}
                className="text-sm"
              />
            </label>
          )}

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Proof of payment (screenshot / receipt)</span>
            <input
              required
              type="file"
              accept="image/*"
              onChange={async (e) => {
                const file = e.target.files?.[0];
                if (file) setProofImage(await fileToDataUri(file));
              }}
              className="text-sm"
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="text-sm font-medium">Note (optional)</span>
            <input
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. August maintenance, flat 4B"
              className="rounded-lg border border-line bg-transparent px-3 py-2 text-sm outline-none focus:border-accent"
            />
          </label>

          {error && <p className="text-sm text-danger">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="rounded-lg bg-accent text-white text-sm font-medium py-2.5 disabled:opacity-60"
          >
            {busy ? "Submitting…" : "Submit payment"}
          </button>
        </form>
      </section>

      <section>
        <h2 className="text-lg font-semibold mb-4">Your payments</h2>
        {loading ? (
          <p className="text-sm text-foreground-soft">Loading…</p>
        ) : transactions.length === 0 ? (
          <p className="text-sm text-foreground-soft">No payments submitted yet.</p>
        ) : (
          <ul className="flex flex-col gap-3">
            {transactions.map((t) => (
              <li key={t.id} className="rounded-xl border border-line bg-surface p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-mono text-sm tabular-nums">₹{t.amount} + ₹{t.chargesFee} fee</p>
                    <p className="text-xs text-foreground-soft mt-0.5">
                      {t.method === "UPI_ID" ? `Paid to ${t.upiId}` : "Paid via QR upload"} ·{" "}
                      {new Date(t.createdAt).toLocaleString()}
                    </p>
                    {t.note && <p className="text-xs text-foreground-soft mt-1">{t.note}</p>}
                    {t.decisionNote && (
                      <p className="text-xs text-foreground-soft mt-1">Approver note: {t.decisionNote}</p>
                    )}
                  </div>
                  <StatusBadge status={t.status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
