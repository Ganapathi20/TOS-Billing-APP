"use client";

import { useEffect, useMemo, useState } from "react";
import { StatusBadge } from "@/components/StatusBadge";
import type { Transaction, TransactionStatus } from "@/lib/types";

const TABS: { key: TransactionStatus; label: string }[] = [
  { key: "PENDING_APPROVAL", label: "Pending" },
  { key: "APPROVED", label: "Approved" },
  { key: "REJECTED", label: "Rejected" },
  { key: "REFUNDED", label: "Refunded" },
];

function fileToDataUri(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

export function ApproverDashboard() {
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState<TransactionStatus>("PENDING_APPROVAL");
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState("");

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

  const filtered = useMemo(() => transactions.filter((t) => t.status === tab), [transactions, tab]);
  const counts = useMemo(() => {
    const map: Record<string, number> = {};
    for (const t of transactions) map[t.status] = (map[t.status] ?? 0) + 1;
    return map;
  }, [transactions]);

  async function decide(id: string, action: "approve" | "reject") {
    setError("");
    setBusyId(id);
    try {
      const res = await fetch(`/api/transactions/${id}/decision`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not record decision");
      await loadTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusyId(null);
    }
  }

  async function refund(id: string, file: File) {
    setError("");
    setBusyId(id);
    try {
      const refundImage = await fileToDataUri(file);
      const res = await fetch(`/api/transactions/${id}/refund`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refundImage }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error ?? "Could not process refund");
      await loadTransactions();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    } finally {
      setBusyId(null);
    }
  }

  return (
    <main className="mx-auto max-w-3xl px-4 py-8 flex flex-col gap-6">
      <div className="flex gap-2 overflow-x-auto">
        {TABS.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`rounded-lg border px-3 py-1.5 text-sm whitespace-nowrap ${
              tab === t.key ? "border-accent bg-accent-soft text-accent" : "border-line text-foreground-soft"
            }`}
          >
            {t.label} {counts[t.key] ? <span className="font-mono">({counts[t.key]})</span> : null}
          </button>
        ))}
      </div>

      {error && <p className="text-sm text-danger">{error}</p>}

      {loading ? (
        <p className="text-sm text-foreground-soft">Loading…</p>
      ) : filtered.length === 0 ? (
        <p className="text-sm text-foreground-soft">Nothing here.</p>
      ) : (
        <ul className="flex flex-col gap-3">
          {filtered.map((t) => (
            <li key={t.id} className="rounded-xl border border-line bg-surface p-4">
              <div className="flex items-start justify-between gap-3 mb-3">
                <div>
                  <p className="font-medium text-sm">{t.user.name}</p>
                  <p className="text-xs text-foreground-soft">{t.user.mobile}</p>
                </div>
                <StatusBadge status={t.status} />
              </div>

              <p className="font-mono text-sm tabular-nums mb-1">
                ₹{t.amount} + ₹{t.chargesFee} fee = ₹{t.chargesTotal}
              </p>
              <p className="text-xs text-foreground-soft mb-3">
                {t.method === "UPI_ID" ? `Paid to ${t.upiId}` : "Paid via QR upload"} ·{" "}
                {new Date(t.createdAt).toLocaleString()}
              </p>

              <div className="flex flex-wrap gap-3 mb-3">
                {t.method === "QR_UPLOAD" && t.qrImage && (
                  <a href={t.qrImage} target="_blank" rel="noreferrer" className="block">
                    <img src={t.qrImage} alt="QR code" className="h-20 w-20 rounded-md border border-line object-cover" />
                    <span className="text-xs text-foreground-soft">QR code</span>
                  </a>
                )}
                {t.proofImage && (
                  <a href={t.proofImage} target="_blank" rel="noreferrer" className="block">
                    <img src={t.proofImage} alt="Payment proof" className="h-20 w-20 rounded-md border border-line object-cover" />
                    <span className="text-xs text-foreground-soft">Payment proof</span>
                  </a>
                )}
                {t.refundImage && (
                  <a href={t.refundImage} target="_blank" rel="noreferrer" className="block">
                    <img src={t.refundImage} alt="Refund proof" className="h-20 w-20 rounded-md border border-line object-cover" />
                    <span className="text-xs text-foreground-soft">Refund proof</span>
                  </a>
                )}
              </div>

              {t.note && <p className="text-xs text-foreground-soft mb-3">Resident note: {t.note}</p>}

              {t.status === "PENDING_APPROVAL" && (
                <div className="flex gap-2">
                  <button
                    onClick={() => decide(t.id, "approve")}
                    disabled={busyId === t.id}
                    className="rounded-lg bg-accent text-white text-sm font-medium px-3 py-1.5 disabled:opacity-60"
                  >
                    Approve
                  </button>
                  <button
                    onClick={() => decide(t.id, "reject")}
                    disabled={busyId === t.id}
                    className="rounded-lg border border-danger text-danger text-sm font-medium px-3 py-1.5 disabled:opacity-60"
                  >
                    Reject
                  </button>
                </div>
              )}

              {t.status === "APPROVED" && (
                <label className="inline-flex items-center gap-2 text-sm text-accent cursor-pointer">
                  <span className="rounded-lg border border-accent px-3 py-1.5">
                    {busyId === t.id ? "Uploading…" : "Issue refund (upload proof)"}
                  </span>
                  <input
                    type="file"
                    accept="image/*"
                    className="hidden"
                    disabled={busyId === t.id}
                    onChange={(e) => {
                      const file = e.target.files?.[0];
                      if (file) refund(t.id, file);
                    }}
                  />
                </label>
              )}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
