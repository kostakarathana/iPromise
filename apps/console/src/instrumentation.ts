export async function register() {
  if (process.env.NEXT_RUNTIME !== "nodejs") return;

  const { assertConsoleRuntimeConfiguration } = await import(
    "@/lib/runtime-config"
  );
  assertConsoleRuntimeConfiguration();
}
