"use client";

import { useParams, usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { workspaceApi } from "@/lib/api";
import { Workspace } from "@/types";
import Navbar from "@/components/layout/Navbar";
import { cn } from "@/lib/utils";
import { MessageSquare, Database, FileText, BarChart2 } from "lucide-react";

const tabs = [
  { label: "Chat", icon: MessageSquare, href: "" },
  { label: "Sources", icon: Database, href: "/sources" },
  { label: "Reports", icon: FileText, href: "/reports" },
  { label: "Analytics", icon: BarChart2, href: "/analytics" },
];

export default function WorkspaceLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const params = useParams();
  const pathname = usePathname();
  const router = useRouter();
  const id = params.id as string;

  const { data: workspace } = useQuery<Workspace>({
    queryKey: ["workspace", id],
    queryFn: () => workspaceApi.getOne(id),
  });

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Navbar />

      {/* Workspace header + tabs */}
      <div className="border-b border-border bg-background">
        <div className="max-w-7xl mx-auto px-4">
          {/* Workspace name */}
          <div className="py-2 flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Workspace</span>
            <span className="text-xs text-muted-foreground">/</span>
            <span className="font-heading font-semibold text-sm">
              {workspace?.name ?? "Loading..."}
            </span>
          </div>

          {/* Tab navigation */}
          <div className="flex items-center gap-1">
            {tabs.map((tab) => {
              const href = `/w/${id}${tab.href}`;
              const isActive =
                tab.href === ""
                  ? pathname === `/w/${id}`
                  : pathname.startsWith(href);

              return (
                <button
                  key={tab.label}
                  onClick={() => router.push(href)}
                  className={cn(
                    "flex items-center gap-2 px-3 py-2 text-sm font-medium border-b-2 transition-colors",
                    isActive
                      ? "border-primary text-primary"
                      : "border-transparent text-muted-foreground hover:text-foreground",
                  )}
                >
                  <tab.icon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Page content */}
      <div className="flex-1 max-w-7xl mx-auto w-full px-4 py-4">
        {children}
      </div>
    </div>
  );
}
