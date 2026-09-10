import { redirect } from "next/navigation";
import { getSession } from "@/lib/session";

export default async function Home() {
  const session = await getSession();

  if (!session) {
    redirect(process.env.SKIP_AUTH === "true" ? "/api/test/login?role=USER" : "/login");
  }
  redirect(session.role === "APPROVER" ? "/approver" : "/user");
}
