import { cn } from "@/lib/utils";

export function BrandMark({ className }: { className?: string }) {
  return (
    <svg
      aria-hidden="true"
      className={cn("shrink-0", className)}
      fill="none"
      focusable="false"
      viewBox="0 0 24 24"
    >
      <path
        d="M6.5 6.5h-.8A2.7 2.7 0 0 0 3 9.2v2.3h3.2V9.3H4.9"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
      <path
        d="m8.2 12.2 3.6 3.6L21 6.6"
        stroke="currentColor"
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth="2.2"
      />
    </svg>
  );
}
