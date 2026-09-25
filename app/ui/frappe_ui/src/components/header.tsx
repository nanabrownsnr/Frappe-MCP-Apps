import React from "react";
import { cn } from "@/lib/utils";

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
          <div className="h-full bg-primary animate-topLoader" />
        </div>
      )}

      <div>
        <h1 className="text-base font-bold tracking-tight">{title}</h1>
        <p className="text-sm text-gray-4">{subtitle}</p>
      </div>
      {children}
    </header>
  );
}
