import { cookies } from "next/headers";

import { AccessGate } from "@/components/access-gate";
import { PromiseDashboard } from "@/components/promise-dashboard";
import {
  CONSOLE_SESSION_COOKIE,
  isConsoleAccessConfigured,
  verifyConsoleSession,
} from "@/lib/console-auth";

// Authentication is runtime configuration on Cloud Run. Never prerender a
// tokenless build into a permanently public dashboard.
export const dynamic = "force-dynamic";

export default async function HomePage() {
  if (isConsoleAccessConfigured()) {
    const cookieStore = await cookies();
    if (!verifyConsoleSession(cookieStore.get(CONSOLE_SESSION_COOKIE)?.value)) {
      return <AccessGate />;
    }
  }
  return <PromiseDashboard />;
}
