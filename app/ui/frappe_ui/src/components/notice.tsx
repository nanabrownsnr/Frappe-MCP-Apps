import { AlertCircle, CircleAlert, CircleCheck, Info } from "lucide-react";
import type { ReactNode } from "react";
import { Alert, AlertAction, AlertDescription } from "@/components/ui/alert";
import { cn } from "@/lib/utils";

const icons = {
  info: Info,
  success: CircleCheck,
  error: CircleAlert,
  warn: AlertCircle,
} as const;

function Notice({
  tone,
  text,
  className,
  actions,
}: {
  tone: "info" | "success" | "error" | "warn";
  text: string;
  className?: string;
  actions?: ReactNode;
}) {
  const Icon = icons[tone];

  return (
    <Alert variant={tone} className={cn("", className)}>
      <Icon aria-hidden />
      <AlertDescription className="text-[13px] leading-relaxed">
        <span>{text}</span>
      </AlertDescription>
      {actions ? (
        <AlertAction className="flex top-auto self-center  flex-wrap gap-2">
          {actions}
        </AlertAction>
      ) : null}
    </Alert>
  );
}

export default Notice;
