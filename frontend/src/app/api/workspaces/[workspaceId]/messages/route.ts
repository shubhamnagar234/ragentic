import { auth } from "@/lib/auth";
import { serverFetch } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

interface Props {
  params: Promise<{ workspaceId: string }>;
}

export const dynamic = 'force-dynamic';


export async function GET(_request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId } = await params;
  const url = new URL(_request.url);
  const sessionId = url.searchParams.get("session_id");
  const backendUrl = sessionId 
    ? `/api/workspaces/${workspaceId}/messages?session_id=${sessionId}`
    : `/api/workspaces/${workspaceId}/messages`;

  try {
    const data = await serverFetch(
      backendUrl,
      { method: "GET" },
      session.user.id,
    );
    return NextResponse.json(data);
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

export async function DELETE(request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId } = await params;
  const url = new URL(request.url);
  const sessionId = url.searchParams.get("session_id");
  const backendUrl = sessionId
    ? `/api/workspaces/${workspaceId}/messages?session_id=${sessionId}`
    : `/api/workspaces/${workspaceId}/messages`;

  try {
    await serverFetch(backendUrl, { method: "DELETE" }, session.user.id);
    return new NextResponse(null, { status: 204 });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: message }, { status: 500 });
  }
}

