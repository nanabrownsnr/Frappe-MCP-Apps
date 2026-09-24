import React from "react";
import { cn } from "@/lib/utils";

export default function Header({
  title,
  subtitle,
  children,
  className,
}: {
  title: React.ReactNode;
  subtitle: React.ReactNode;
  children?: React.ReactNode;
  className?: string;
}) {
  return (
    <header
      className={cn(
        "px-4 py-2 sticky top-0 z-10 bg-host-bg flex border-b items-center flex-wrap justify-between gap-3",
        className
      )}
    >
      <div>
        <h1 className="text-base font-bold tracking-tight">{title}</h1>
        <p className="text-sm text-gray-4">{subtitle}</p>
      </div>
      {children}
    </header>
  );
}
