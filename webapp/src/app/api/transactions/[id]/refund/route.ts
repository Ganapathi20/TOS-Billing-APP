import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getSession } from "@/lib/session";

const MAX_IMAGE_LENGTH = 2_000_000;

export async function POST(request: NextRequest, ctx: RouteContext<"/api/transactions/[id]/refund">) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (session.role !== "APPROVER") {
    return NextResponse.json({ error: "Only an approver can issue a refund" }, { status: 403 });
  }

  const { id } = await ctx.params;
  const body = await request.json().catch(() => null);
  const refundImage = body?.refundImage;

  if (typeof refundImage !== "string" || !refundImage.startsWith("data:image/") || refundImage.length > MAX_IMAGE_LENGTH) {
    return NextResponse.json({ error: "Upload proof of the refund" }, { status: 400 });
  }

  const existing = await db.transaction.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Transaction not found" }, { status: 404 });
  if (existing.status !== "APPROVED") {
    return NextResponse.json({ error: "Only an approved payment can be refunded" }, { status: 409 });
  }

  const transaction = await db.transaction.update({
    where: { id },
    data: { status: "REFUNDED", refundImage },
  });

  return NextResponse.json({ transaction });
}
