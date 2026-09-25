import React from "react";
import { ChevronLeft } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "./ui/button";
import { useToolCall } from "./tool-call-provider";

export default function Header({
  title,
  subtitle,
  children,
  className,
  isLoading = false,
}: {
  title: React.ReactNode;
  subtitle: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
  isLoading?: boolean;
}) {
  const { canGoBack, popToolCall } = useToolCall();

  return (
    <header
      className={cn(
        "px-4 py-2 sticky top-0 z-10 bg-host-bg flex border-b items-center flex-wrap justify-between gap-3",
        className
      )}
    >
      {/* Top Loader Bar */}
      {isLoading && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-inherit overflow-hidden">
          <div className="h-full bg-primary/60 animate-topLoader" />
        </div>
      )}

      <div className="flex items-center gap-2">
        {canGoBack && (
          <Button
            type="button"
            variant="ghost"
            size="icon-sm"
            aria-label="Back"
            onClick={popToolCall}
          >
            <ChevronLeft />
          </Button>
        )}
        <div>
          <h1 className="text-base font-bold tracking-tight">{title}</h1>
          <p className="text-sm text-gray-4">{subtitle}</p>
        </div>
      </div>
      {children}
    </header>
  );
}
