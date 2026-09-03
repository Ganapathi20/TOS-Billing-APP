/**
 * Illustrative convenience-fee formula: 2% of the maintenance amount,
 * plus a flat ₹3 gateway fee, rounded to the nearest rupee.
 * Replace with the society's real fee schedule when known.
 */
export function computeCharges(amount: number) {
  if (!Number.isFinite(amount) || amount <= 0) {
    throw new Error("amount must be a positive number");
  }
  const fee = Math.round(amount * 0.02) + 3;
  const total = amount + fee;
  return { amount, fee, total };
}
