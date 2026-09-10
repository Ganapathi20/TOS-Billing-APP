import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { TopNav } from "@/components/TopNav";
import { ApproverDashboard } from "./ApproverDashboard";

export default async function ApproverPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "APPROVER") redirect("/user");

  return (
    <>
      <TopNav name={session.name} role={session.role} testMode={process.env.SKIP_AUTH === "true"} />
      <ApproverDashboard />
    </>
  );
}
