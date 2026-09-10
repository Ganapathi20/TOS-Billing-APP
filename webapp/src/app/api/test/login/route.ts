import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { createSessionCookie } from "@/lib/session";

// Test-only, one-click sign-in that skips OTP entirely — for trying out the
// app without a real phone number handy. Completely inert unless SKIP_AUTH
// is explicitly set to "true"; never set that on a real deployment, since
// this route would let anyone sign in as either role with no verification.
const TEST_ACCOUNTS = {
  USER: { mobile: "9999900001", name: "Test Resident" },
  APPROVER: { mobile: "9999900002", name: "Test Approver" },
} as const;

export async function GET(request: NextRequest) {
  if (process.env.SKIP_AUTH !== "true") {
    return NextResponse.json({ error: "Not found" }, { status: 404 });
  }

  const roleParam = request.nextUrl.searchParams.get("role");
  const role = roleParam === "APPROVER" ? "APPROVER" : "USER";
  const account = TEST_ACCOUNTS[role];

  const user = await db.user.upsert({
    where: { mobile: account.mobile },
    update: {},
    create: { mobile: account.mobile, name: account.name, role },
  });

  await createSessionCookie({ userId: user.id, mobile: user.mobile, name: user.name, role: user.role });

  return NextResponse.redirect(new URL(role === "APPROVER" ? "/approver" : "/user", request.url));
}
