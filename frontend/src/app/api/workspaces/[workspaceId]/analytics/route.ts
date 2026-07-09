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
  const data = await serverFetch(
    `/api/workspaces/${workspaceId}/analytics`,
    { method: "GET" },
    session.user.id,
  );
  return NextResponse.json(data);
}
