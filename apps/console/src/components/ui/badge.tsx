import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";

import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex w-fit items-center gap-1.5 rounded-md border px-2 py-0.5 text-xs font-medium leading-5",
  {
    variants: {
      variant: {
        neutral: "border-border bg-secondary text-muted-foreground",
        danger:
          "border-status-danger/25 bg-status-danger/10 text-status-danger",
        success:
          "border-status-success/25 bg-status-success/10 text-status-success",
        warning:
          "border-status-warning/25 bg-status-warning/10 text-status-warning",
        info: "border-status-info/25 bg-status-info/10 text-status-info",
      },
    },
    defaultVariants: { variant: "neutral" },
  },
);

type BadgeProps = React.ComponentProps<"span"> &
  VariantProps<typeof badgeVariants>;

export function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <span className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}
