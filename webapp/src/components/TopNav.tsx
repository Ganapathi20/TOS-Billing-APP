"use client";

import { useRouter } from "next/navigation";

export function TopNav({ name, role }: { name: string; role: "USER" | "APPROVER" }) {
  const router = useRouter();

  async function logout() {
    await fetch("/api/auth/logout", { method: "POST" });
    router.push("/login");
    router.refresh();
  }

  return (
    <header className="border-b border-line">
      <div className="mx-auto max-w-3xl px-4 py-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-mono uppercase tracking-wider text-accent">Towers Online Services</p>
          <p className="text-sm text-foreground-soft">
            {name} · {role === "APPROVER" ? "Approver" : "Resident"}
          </p>
        </div>
        <button
          onClick={logout}
          className="text-sm text-foreground-soft border border-line rounded-lg px-3 py-1.5 hover:border-accent hover:text-accent"
        >
          Sign out
        </button>
      </div>
    </header>
  );
}
