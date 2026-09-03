import { db } from "@/lib/db";

const OTP_TTL_MINUTES = 5;

export function normalizeMobile(raw: string) {
  return raw.replace(/\D/g, "").slice(-10);
}

export async function issueOtp(mobile: string) {
  const code = Math.floor(100000 + Math.random() * 900000).toString();
  const expiresAt = new Date(Date.now() + OTP_TTL_MINUTES * 60 * 1000);

  await db.otp.create({ data: { mobile, code, expiresAt } });

  return { code, expiresAt };
}

export async function isOtpValid(mobile: string, code: string) {
  const otp = await db.otp.findFirst({
    where: { mobile, code, consumed: false, expiresAt: { gt: new Date() } },
    orderBy: { createdAt: "desc" },
  });
  return otp !== null;
}

// Only call this once the sign-in is actually going to complete — a check
// that stops short of finishing (e.g. asking a new user for their name and
// role) must not consume the code, or the follow-up submission with those
// fields will find the code already used.
export async function consumeOtp(mobile: string, code: string) {
  const otp = await db.otp.findFirst({
    where: { mobile, code, consumed: false, expiresAt: { gt: new Date() } },
    orderBy: { createdAt: "desc" },
  });

  if (!otp) return false;

  await db.otp.update({ where: { id: otp.id }, data: { consumed: true } });
  return true;
}
