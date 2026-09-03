import { NextRequest, NextResponse } from "next/server";
import { db } from "@/lib/db";
import { consumeOtp, isOtpValid, normalizeMobile } from "@/lib/otp";
import { createSessionCookie } from "@/lib/session";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const mobile = normalizeMobile(String(body?.mobile ?? ""));
  const code = String(body?.code ?? "");
  const name = typeof body?.name === "string" ? body.name.trim() : "";
  const role = body?.role === "APPROVER" ? "APPROVER" : body?.role === "USER" ? "USER" : null;

  if (mobile.length !== 10 || code.length !== 6) {
    return NextResponse.json({ error: "Missing mobile or code" }, { status: 400 });
  }

  if (!(await isOtpValid(mobile, code))) {
    return NextResponse.json({ error: "That code is invalid or has expired" }, { status: 401 });
  }

  let user = await db.user.findUnique({ where: { mobile } });

  if (!user) {
    if (!name || !role) {
      // Don't consume the code yet — the client will resubmit the same
      // code along with name/role once it has them.
      return NextResponse.json(
        { error: "New account: name and role are required", newAccount: true },
        { status: 422 }
      );
    }
    user = await db.user.create({ data: { mobile, name, role } });
  }

  await consumeOtp(mobile, code);

  await createSessionCookie({
    userId: user.id,
    mobile: user.mobile,
    name: user.name,
    role: user.role,
  });

  return NextResponse.json({ user });
}
