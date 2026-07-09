import { create } from "zustand";
import { Workspace, Source, Session, SourceCitation } from "@/types";

interface WorkspaceStore {
  // Current workspace
  currentWorkspace: Workspace | null;
  setCurrentWorkspace: (workspace: Workspace | null) => void;

  // Sources
  sources: Source[];
  setSources: (sources: Source[]) => void;
  addSource: (source: Source) => void;
  updateSource: (id: string, updates: Partial<Source>) => void;
  removeSource: (id: string) => void;

  // Sessions
  sessions: Session[];
  setSessions: (sessions: Session[]) => void;
  activeSessionId: string | null;
  setActiveSessionId: (id: string | null) => void;
  addSession: (session: Session) => void;

  // Source filter
  activeSourceIds: string[];
  setActiveSourceIds: (ids: string[]) => void;
  toggleSourceFilter: (id: string) => void;
  clearSourceFilter: () => void;
  // UI state
  showEvalPanel: boolean;
  toggleEvalPanel: () => void;
  activeCitation: SourceCitation | null;
  setActiveCitation: (citation: SourceCitation | null) => void;
}

export const useWorkspaceStore = create<WorkspaceStore>((set) => ({
  // Current workspace
  currentWorkspace: null,
  setCurrentWorkspace: (workspace) => set({ currentWorkspace: workspace }),

  // Sources
  sources: [],
  setSources: (sources) => set({ sources }),
  addSource: (source) =>
    set((state) => ({ sources: [...state.sources, source] })),
  updateSource: (id, updates) =>
    set((state) => ({
      sources: state.sources.map((s) =>
        s.id === id ? { ...s, ...updates } : s,
      ),
    })),
  removeSource: (id) =>
    set((state) => ({
      sources: state.sources.filter((s) => s.id !== id),
    })),

  // Sessions
  sessions: [],
  setSessions: (sessions) => set({ sessions }),
  activeSessionId: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  addSession: (session) => 
    set((state) => ({ sessions: [...state.sessions, session] })),

  // Source filter
  activeSourceIds: [],
  setActiveSourceIds: (ids) => set({ activeSourceIds: ids }),
  toggleSourceFilter: (id) =>
    set((state) => ({
      activeSourceIds: state.activeSourceIds.includes(id)
        ? state.activeSourceIds.filter((s) => s !== id)
        : [...state.activeSourceIds, id],
    })),
  clearSourceFilter: () => set({ activeSourceIds: [] }),

  // UI state
  showEvalPanel: false, // Default hidden based on user request
  toggleEvalPanel: () => set((state) => ({ showEvalPanel: !state.showEvalPanel })),
  activeCitation: null,
  setActiveCitation: (citation) => set({ activeCitation: citation }),
}));
