import { auth } from "@/lib/auth";
import { generateToken } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface Props {
  params: Promise<{ workspaceId: string }>;
}

export async function POST(request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session?.user?.id) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId } = await params;
  const body = await request.json();

  // Generate JWT token
  const token = await generateToken(session.user.id);

  // Forward SSE stream from FastAPI to browser
  const response = await fetch(
    `${API_URL}/api/workspaces/${workspaceId}/chat`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    },
  );

  if (!response.ok) {
    return NextResponse.json(
      { error: "Chat request failed" },
      { status: response.status },
    );
  }

  return new NextResponse(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
      "X-Accel-Buffering": "no",
    },
  });
}
