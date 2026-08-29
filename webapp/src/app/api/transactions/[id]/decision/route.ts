import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { getSession } from "@/lib/session";

export async function POST(request: NextRequest, ctx: RouteContext<"/api/transactions/[id]/decision">) {
  const session = await getSession();
  if (!session) return NextResponse.json({ error: "Not signed in" }, { status: 401 });
  if (session.role !== "APPROVER") {
    return NextResponse.json({ error: "Only an approver can decide on a payment" }, { status: 403 });
  }

  const { id } = await ctx.params;
  const body = await request.json().catch(() => null);
  const action = body?.action === "approve" ? "APPROVED" : body?.action === "reject" ? "REJECTED" : null;
  const decisionNote = typeof body?.note === "string" ? body.note.trim().slice(0, 500) : null;

  if (!action) {
    return NextResponse.json({ error: "action must be 'approve' or 'reject'" }, { status: 400 });
  }

  const existing = await db.transaction.findUnique({ where: { id } });
  if (!existing) return NextResponse.json({ error: "Transaction not found" }, { status: 404 });
  if (existing.status !== "PENDING_APPROVAL") {
    return NextResponse.json({ error: "This payment has already been decided" }, { status: 409 });
  }

  const transaction = await db.transaction.update({
    where: { id },
    data: { status: action, decisionNote, approverId: session.userId },
  });

  return NextResponse.json({ transaction });
}
