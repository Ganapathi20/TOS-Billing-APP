import { NextRequest, NextResponse } from "next/server";
import { computeCharges } from "@/lib/charges";

export async function GET(request: NextRequest) {
  const amount = Number(request.nextUrl.searchParams.get("amount"));

  if (!Number.isFinite(amount) || amount <= 0) {
    return NextResponse.json({ error: "amount must be a positive number" }, { status: 400 });
  }

  return NextResponse.json(computeCharges(amount));
}
