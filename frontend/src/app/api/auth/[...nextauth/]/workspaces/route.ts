import { auth } from "@/lib/auth";
import { serverFetch } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

export async function GET() {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const data = await serverFetch(
    "/api/workspaces/",
    { method: "GET" },
    session.user.id,
  );
  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json();
  const data = await serverFetch(
    "/api/workspaces/",
    {
      method: "POST",
      body: JSON.stringify(body),
    },
    session.user.id,
  );
  return NextResponse.json(data);
}
