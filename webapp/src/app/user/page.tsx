import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";
import { TopNav } from "@/components/TopNav";
import { UserDashboard } from "./UserDashboard";

export default async function UserPage() {
  const session = await getSession();
  if (!session) redirect("/login");
  if (session.role !== "USER") redirect("/approver");

  return (
    <>
      <TopNav name={session.name} role={session.role} testMode={process.env.SKIP_AUTH === "true"} />
      <UserDashboard />
    </>
  );
}
