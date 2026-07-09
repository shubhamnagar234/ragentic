import { auth } from "@/lib/auth"
import { serverFetch } from "@/lib/api"
import { NextRequest, NextResponse } from "next/server"

interface Props {
  params: Promise<{ workspaceId: string }>
}

export const dynamic = 'force-dynamic';


export async function GET(_request: NextRequest, { params }: Props) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { workspaceId } = await params
  try {
    const data = await serverFetch(
      `/api/workspaces/${workspaceId}/sources`,
      { method: "GET" },
      session.user.id,
    )
    return NextResponse.json(data)
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return NextResponse.json({ error: message }, { status: 500 })
  }
}

export async function POST(request: NextRequest, { params }: Props) {
  const session = await auth()
  if (!session) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }

  const { workspaceId } = await params
  const body = await request.json()
  const data = await serverFetch(
    `/api/workspaces/${workspaceId}/sources`,
    {
      method: "POST",
      body: JSON.stringify(body),
    },
    session.user.id,
  )
  return NextResponse.json(data)
}