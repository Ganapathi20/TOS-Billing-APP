"use client";

import { useRouter } from "next/navigation";

export function TopNav({
  name,
  role,
  testMode = false,
}: {
  name: string;
  role: "USER" | "APPROVER";
  testMode?: boolean;
}) {
  const router = useRouter();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="border-b border-line">
      {testMode && (
        <div className="bg-warn-soft text-warn text-xs font-mono text-center py-1.5">
          TEST MODE — login is bypassed (SKIP_AUTH=true). Remove before real use.
        </div>
      )}
      <div className="mx-auto max-w-3xl px-4 py-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-accent">Towers Online Services</p>
          <p className="text-sm text-foreground-soft">
            {name} · {role === "APPROVER" ? "Approver" : "Resident"}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {testMode && (
            <a
              href={`/api/test/login?role=${role === "APPROVER" ? "USER" : "APPROVER"}`}
              className="text-sm text-accent border border-accent rounded-lg px-3 py-1.5 hover:bg-accent-soft"
            >
              Switch to {role === "APPROVER" ? "Resident" : "Approver"} view
            </a>
          )}
          <button
            onClick={logout}
            className="text-sm text-foreground-soft border border-line rounded-lg px-3 py-1.5 hover:border-accent hover:text-accent"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>
  );
}
