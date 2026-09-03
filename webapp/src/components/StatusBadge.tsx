const STYLES: Record<string, string> = {
  PENDING_APPROVAL: "bg-warn-soft text-warn",
  APPROVED: "bg-accent-soft text-accent",
  REJECTED: "bg-danger-soft text-danger",
  REFUNDED: "bg-accent-soft text-accent",
};

const LABELS: Record<string, string> = {
  PENDING_APPROVAL: "Pending approval",
  APPROVED: "Approved",
  REJECTED: "Rejected",
  REFUNDED: "Refunded",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${STYLES[status] ?? ""}`}>
      {LABELS[status] ?? status}
    </span>
  );
}
