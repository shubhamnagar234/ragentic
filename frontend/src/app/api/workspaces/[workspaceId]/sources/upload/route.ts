import { auth } from "@/lib/auth";
import { generateToken } from "@/lib/api";
import { NextRequest, NextResponse } from "next/server";

const API_URL = process.env.NEXT_PUBLIC_API_URL as string;

interface Props {
  params: Promise<{ workspaceId: string }>;
}

export async function POST(request: NextRequest, { params }: Props) {
  const session = await auth();
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { workspaceId } = await params;
  
  // Forward the raw request stream to preserve multipart boundaries
  const token = await generateToken(session.user.id);
  
  const response = await fetch(`${API_URL}/api/workspaces/${workspaceId}/sources/upload`, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${token}`,
      "Content-Type": request.headers.get("content-type") || "",
    },
    body: request.body,
    // @ts-expect-error - Node.js fetch requires duplex: 'half' for streams, but it's not yet in the TS standard lib DOM types
    duplex: "half",
  });
  
  if (!response.ok) {
    return NextResponse.json(
      { error: `Backend error: ${response.statusText}` },
      { status: response.status }
    );
  }
  
  const data = await response.json();
  return NextResponse.json(data);
}
