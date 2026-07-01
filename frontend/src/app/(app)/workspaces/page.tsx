"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspaceApi } from "@/lib/api";
import { Workspace } from "@/types";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import Navbar from "@/components/layout/Navbar";
import { Plus, Folder, ArrowRight, Sparkles } from "lucide-react";
import { motion } from "motion/react";

export default function WorkspacesPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [newWorkspaceName, setNewWorkspaceName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);

  // Fetch workspaces
  const { data: workspaces = [], isLoading } = useQuery({
    queryKey: ["workspaces"],
    queryFn: () => workspaceApi.getAll(),
  });

  // Create workspace
  const createMutation = useMutation({
    mutationFn: (name: string) => workspaceApi.create(name),
    onSuccess: (newWorkspace: Workspace) => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      setDialogOpen(false);
      setNewWorkspaceName("");
      router.push(`/w/${newWorkspace.id}`);
    },
  });

  const handleCreate = () => {
    if (!newWorkspaceName.trim()) return;
    createMutation.mutate(newWorkspaceName.trim());
  };

  return (
    <div className="min-h-screen bg-background">
      <Navbar />

      <main className="max-w-4xl mx-auto px-4 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="font-heading text-2xl font-bold tracking-tight">
              Workspaces
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Your knowledge workspaces
            </p>
          </div>

          {/* Create workspace dialog */}
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild>
              <Button size="sm" className="gap-2">
                <Plus className="w-4 h-4" />
                New workspace
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle className="font-heading">
                  Create workspace
                </DialogTitle>
              </DialogHeader>
              <div className="space-y-4 pt-2">
                <Input
                  placeholder="e.g. Next.js Research"
                  value={newWorkspaceName}
                  onChange={(e) => setNewWorkspaceName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleCreate()}
                  autoFocus
                />
                <Button
                  className="w-full"
                  onClick={handleCreate}
                  disabled={
                    !newWorkspaceName.trim() || createMutation.isPending
                  }
                >
                  {createMutation.isPending ? "Creating..." : "Create"}
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Loading */}
        {isLoading && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-24 rounded-xl border border-border bg-muted animate-pulse"
              />
            ))}
          </div>
        )}

        {/* Empty state */}
        {!isLoading && workspaces.length === 0 && (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-muted-foreground" />
            </div>
            <div className="text-center">
              <h3 className="font-heading font-semibold">No workspaces yet</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Create your first workspace to get started
              </p>
            </div>
            <Button
              size="sm"
              className="gap-2"
              onClick={() => setDialogOpen(true)}
            >
              <Plus className="w-4 h-4" />
              Create workspace
            </Button>
          </div>
        )}

        {/* Workspace grid */}
        {!isLoading && workspaces.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {workspaces.map((workspace: Workspace, i: number) => (
              <motion.div
                key={workspace.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.05 }}
                className="group border border-border rounded-xl p-5 bg-card hover:border-primary/50 hover:shadow-sm cursor-pointer transition-all"
                onClick={() => router.push(`/w/${workspace.id}`)}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                      <Folder className="w-4 h-4 text-primary" />
                    </div>
                    <div>
                      <h3 className="font-heading font-semibold text-sm">
                        {workspace.name}
                      </h3>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {new Date(workspace.created_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                  <ArrowRight className="w-4 h-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
