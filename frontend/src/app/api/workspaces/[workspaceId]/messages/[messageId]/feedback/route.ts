import { auth } from "@/lib/auth";
import { serverFetch } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

interface Props {
  params: Promise<{ workspaceId: string; messageId: string }>;
}

export async function PATCH(request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId, messageId } = await params;
  const body = await request.json();
  
  const data = await serverFetch(
    `/api/workspaces/${workspaceId}/messages/${messageId}/feedback`,
    {
      method: "PATCH",
      body: JSON.stringify(body),
    },
    session.user.id,
  );
  
  return NextResponse.json(data);
}
