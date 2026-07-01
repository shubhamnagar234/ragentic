import { auth } from "@/lib/auth";
import { serverFetch } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

interface Props {
  params: Promise<{ workspaceId: string; reportId: string }>;
}

export async function GET(_request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId, reportId } = await params;
  const data = await serverFetch(
    `/api/workspaces/${workspaceId}/reports/${reportId}`,
    { method: "GET" },
    session.user.id,
  );
  return NextResponse.json(data);
}

export async function DELETE(_request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId, reportId } = await params;
  await serverFetch(
    `/api/workspaces/${workspaceId}/reports/${reportId}`,
    { method: "DELETE" },
    session.user.id,
  );
  return new NextResponse(null, { status: 204 });
}
