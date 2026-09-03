import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getSession } from "@/lib/session";
import { computeCharges } from "@/lib/charges";

const MAX_IMAGE_LENGTH = 2_000_000; // ~1.5MB image as base64 text

function isValidImage(value: unknown): value is string {
  return typeof value === "string" && value.startsWith("data:image/") && value.length <= MAX_IMAGE_LENGTH;
}

export async function GET() {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Not signed in" }, { status: 401 });

  const transactions = await db.transaction.findMany({
    where: session.role === "APPROVER" ? {} : { userId: session.userId },
    orderBy: { createdAt: "desc" },
    include: {
      user: { select: { name: true, mobile: true } },
      approver: { select: { name: true } },
    },
  });

  return NextResponse.json({ transactions });
}

export async function POST(request: NextRequest) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (session.role !== "USER") {
    return NextResponse.json({ error: "Only residents can submit a payment" }, { status: 403 });
  }

  const body = await request.json().catch(() => null);
  const amount = Number(body?.amount);
  const method = body?.method === "QR_UPLOAD" ? "QR_UPLOAD" : body?.method === "UPI_ID" ? "UPI_ID" : null;
  const upiId = typeof body?.upiId === "string" ? body.upiId.trim() : "";
  const qrImage = body?.qrImage;
  const proofImage = body?.proofImage;
  const note = typeof body?.note === "string" ? body.note.trim().slice(0, 500) : null;

  if (!Number.isFinite(amount) || amount <= 0) {
    return NextResponse.json({ error: "Enter a valid amount" }, { status: 400 });
  }
  if (!method) {
    return NextResponse.json({ error: "Choose a payment method" }, { status: 400 });
  }
  if (method === "UPI_ID" && !upiId) {
    return NextResponse.json({ error: "Enter the UPI ID you paid to" }, { status: 400 });
  }
  if (method === "QR_UPLOAD" && !isValidImage(qrImage)) {
    return NextResponse.json({ error: "Upload the QR code image" }, { status: 400 });
  }
  if (!isValidImage(proofImage)) {
    return NextResponse.json({ error: "Upload proof of payment" }, { status: 400 });
  }

  const { fee, total } = computeCharges(amount);

  const transaction = await db.transaction.create({
    data: {
      amount,
      method,
      upiId: method === "UPI_ID" ? upiId : null,
      qrImage: method === "QR_UPLOAD" ? qrImage : null,
      proofImage,
      note,
      chargesFee: fee,
      chargesTotal: total,
      userId: session.userId,
    },
  });

  return NextResponse.json({ transaction }, { status: 201 });
}
