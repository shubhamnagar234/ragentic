/**
 * Server-only utilities for Next.js API route handlers.
 * This file must NOT be imported in client components.
 */
import { NextResponse } from "next/server";
import { ApiError } from "./api";

/**
 * Shared error handler for Next.js API route handlers.
 * Forwards the upstream HTTP status code when available, otherwise 502.
 *
 * Usage:
 *   } catch (error) {
 *     return handleApiError(error, "workspace");
 *   }
 */
export function handleApiError(error: unknown, label: string): NextResponse {
  if (error instanceof ApiError) {
    console.error(`[${label}] ${error.message}`);
    return NextResponse.json({ error: error.message }, { status: error.status });
  }
  console.error(`[${label}] Unexpected error:`, error);
  return NextResponse.json({ error: "Internal server error" }, { status: 502 });
}
