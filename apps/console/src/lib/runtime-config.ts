import { assertAgentProxyConfiguration } from "@/lib/agent-client";
import { isConsoleAccessConfigured } from "@/lib/console-auth";

export function assertConsoleRuntimeConfiguration(): {
  agentConfigured: boolean;
} {
  // Both helpers throw on an invalid or incomplete Cloud Run configuration.
  // Local development may intentionally omit both integrations.
  isConsoleAccessConfigured();
  return { agentConfigured: assertAgentProxyConfiguration() };
}
