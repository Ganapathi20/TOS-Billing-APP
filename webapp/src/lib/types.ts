export type TransactionStatus = "PENDING_APPROVAL" | "APPROVED" | "REJECTED" | "REFUNDED";
export type PaymentMethod = "UPI_ID" | "QR_UPLOAD";

export type Transaction = {
  id: string;
  amount: number;
  method: PaymentMethod;
  upiId: string | null;
  qrImage: string | null;
  proofImage: string | null;
  refundImage: string | null;
  status: TransactionStatus;
  chargesFee: number;
  chargesTotal: number;
  note: string | null;
  decisionNote: string | null;
  createdAt: string;
  updatedAt: string;
  user: { name: string; mobile: string };
  approver: { name: string } | null;
};
