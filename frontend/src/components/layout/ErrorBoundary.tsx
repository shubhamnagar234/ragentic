"use client";

import { useEffect } from "react";
import { Button } from "@/components/ui/button";
import { AlertCircle, RefreshCw } from "lucide-react";

export default function ErrorBoundary({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="min-h-[400px] flex items-center justify-center">
      <div className="text-center space-y-4 max-w-md">
        <div className="w-12 h-12 rounded-2xl bg-destructive/10 flex items-center justify-center mx-auto">
          <AlertCircle className="w-6 h-6 text-destructive" />
        </div>
        <div>
          <h3 className="font-heading font-semibold">Something went wrong</h3>
          <p className="text-sm text-muted-foreground mt-1">
            {error.message || "An unexpected error occurred"}
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={reset} className="gap-2">
          <RefreshCw className="w-4 h-4" />
          Try again
        </Button>
      </div>
    </div>
  );
}
