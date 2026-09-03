import { NextRequest, NextResponse } from "next/server";
import { issueOtp, normalizeMobile } from "@/lib/otp";

export async function POST(request: NextRequest) {
  const body = await request.json().catch(() => null);
  const mobile = normalizeMobile(String(body?.mobile ?? ""));

  if (mobile.length !== 10) {
    return NextResponse.json({ error: "Enter a valid 10-digit mobile number" }, { status: 400 });
  }

  const { code, expiresAt } = await issueOtp(mobile);

  // No SMS provider is wired up in this demo, so the OTP is handed back
  // directly instead of being sent over SMS. Wire a real provider (Twilio,
  // MSG91, etc.) here before using this in production and drop this field.
  return NextResponse.json({ mobile, devOtp: code, expiresAt });
}
