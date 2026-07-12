"use client";

import { motion, AnimatePresence } from "motion/react";
import { Plus, Folder, Sparkles, X, Bot, Paperclip, Send, MessageSquare, Database, FileText, BarChart2, Cpu, Search, ShieldAlert, RefreshCw, CheckCircle2, GitBranch } from "lucide-react";
import { useEffect, useState } from "react";

const WORKFLOW_STEPS = 6;

export function HeroAnimation() {
  const [step, setStep] = useState(0);

  useEffect(() => {
    let timeoutId: NodeJS.Timeout;

    const runStep = (currentStep: number) => {
      setStep(currentStep);

      let duration = 3500;
      if (currentStep === 1) duration = 2500; // Modal typing
      if (currentStep === 2) duration = 2500; // Workspace list view
      if (currentStep === 3) duration = 2500; // Detail empty view
      if (currentStep === 4) duration = 3500; // Ingesting simulation
      if (currentStep === 5) duration = 7000; // Chatting & Eval population

      timeoutId = setTimeout(() => {
        runStep((currentStep + 1) % WORKFLOW_STEPS);
      }, duration);
    };

    runStep(0);
    return () => clearTimeout(timeoutId);
  }, []);

  return (
    <div className="w-full max-w-[1200px] mx-auto mt-16 rounded-xl border border-border shadow-2xl overflow-hidden flex flex-col h-[700px] relative transition-colors bg-background text-foreground text-sm font-sans select-none pointer-events-none">
      
      {/* Header Navbar (Matching layout/Navbar.tsx) */}
      <div className="h-14 border-b border-border flex items-center px-4 justify-between shrink-0 bg-background">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center">
            <Sparkles className="w-5 h-5 text-primary-foreground" />
          </div>
          <span className="font-bold text-lg tracking-tight font-heading">RAGENTIC</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="w-8 h-8 rounded-full border border-border flex items-center justify-center">
            <span className="text-[10px]">☾</span>
          </div>
          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center text-sm font-heading font-semibold">
            A
          </div>
        </div>
      </div>

      <div className="flex-1 relative overflow-hidden bg-background">
        <AnimatePresence>
          {(step === 0 || step === 1 || step === 2) && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col bg-background"
            >
              {/* Workspaces Header */}
              <div className="max-w-4xl mx-auto w-full pt-10 px-4 flex justify-between items-start">
                <div>
                  <h1 className="font-heading text-2xl font-bold tracking-tight">Workspaces</h1>
                  <p className="text-sm text-muted-foreground mt-1">Your knowledge workspaces</p>
                </div>
                <div className="flex items-center gap-2 bg-primary text-primary-foreground h-9 px-3 rounded-md text-sm font-medium">
                  <Plus className="w-4 h-4" /> New workspace
                </div>
              </div>

              {/* Body */}
              <div className="flex-1 flex flex-col items-center justify-center mt-4">
                {step === 0 && (
                  <div className="flex flex-col items-center justify-center py-24 gap-4">
                    <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center">
                      <Sparkles className="w-8 h-8 text-muted-foreground" />
                    </div>
                    <div className="text-center">
                      <h3 className="font-heading font-semibold">No workspaces yet</h3>
                      <p className="text-sm text-muted-foreground mt-1">Create your first workspace to get started</p>
                    </div>
                    <div className="flex items-center gap-2 bg-primary text-primary-foreground h-9 px-3 rounded-md text-sm font-medium mt-2">
                      <Plus className="w-4 h-4" /> Create workspace
                    </div>
                  </div>
                )}
                
                {step === 2 && (
                  <div className="max-w-4xl mx-auto w-full px-4 mt-8 absolute top-32 left-0 right-0">
                    <div className="group border border-border rounded-xl p-5 bg-card w-72">
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
                            <Folder className="w-4 h-4 text-primary" />
                          </div>
                          <div>
                            <h3 className="font-heading font-semibold text-sm">acme</h3>
                            <p className="text-xs text-muted-foreground mt-0.5">7/12/2026</p>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              {/* Modal Overlay (Step 1) */}
              {step === 1 && (
                <div className="absolute inset-0 bg-background/80 backdrop-blur-sm flex items-center justify-center z-50">
                  <motion.div initial={{ scale: 0.95, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="w-full max-w-lg bg-background border border-border rounded-xl shadow-lg overflow-hidden">
                    <div className="p-6 pb-4 flex flex-col gap-1">
                      <div className="flex justify-between items-center">
                        <span className="font-heading text-lg font-semibold tracking-tight">Create workspace</span>
                        <X className="w-4 h-4 text-muted-foreground opacity-70" />
                      </div>
                    </div>
                    <div className="p-6 pt-2 space-y-4">
                      <div className="h-10 w-full bg-background border border-border rounded-md px-3 flex items-center text-sm shadow-sm">
                        <motion.span initial={{ width: 0, opacity: 0 }} animate={{ width: "auto", opacity: 1 }} transition={{ duration: 1.5 }} className="overflow-hidden whitespace-nowrap border-r border-foreground pr-1 text-foreground">
                          acme
                        </motion.span>
                      </div>
                      <div className="h-10 w-full bg-primary text-primary-foreground rounded-md flex items-center justify-center text-sm font-medium">
                        Create
                      </div>
                    </div>
                  </motion.div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Phase 3, 4, 5: Workspace Detail View */}
        <AnimatePresence>
          {(step >= 3) && (
            <motion.div 
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              className="absolute inset-0 flex flex-col bg-background"
            >
              {/* Subheader */}
              <div className="h-14 border-b border-border flex flex-col px-6 pt-2 shrink-0 bg-background">
                <div className="text-[11px] text-muted-foreground mb-1">Workspace / <span className="text-foreground">acme</span></div>
                <div className="flex gap-8 text-[13px] font-medium text-muted-foreground">
                  <div className="flex items-center gap-1.5 text-foreground border-b-2 border-foreground pb-2"><MessageSquare className="w-3.5 h-3.5" /> Chat</div>
                  <div className="flex items-center gap-1.5 pb-2"><Database className="w-3.5 h-3.5" /> Sources</div>
                  <div className="flex items-center gap-1.5 pb-2"><FileText className="w-3.5 h-3.5" /> Reports</div>
                  <div className="flex items-center gap-1.5 pb-2"><BarChart2 className="w-3.5 h-3.5" /> Analytics</div>
                </div>
              </div>

              <div className="flex-1 flex overflow-hidden">
                {/* Left Sidebar */}
                <div className="w-[280px] border-r border-border p-5 flex flex-col gap-8 overflow-y-auto shrink-0 bg-background/50">
                  <div>
                    <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-4 flex justify-between items-center">
                      CHAT HISTORY <span className="text-foreground flex items-center gap-1"><Plus className="w-3 h-3"/> New</span>
                    </div>
                    <div className="text-xs text-muted-foreground">No history yet</div>
                  </div>

                  <div>
                    <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-4">AGENTS</div>
                    <div className="space-y-1.5">
                      {[
                        { name: "Query analyzer", icon: Cpu },
                        { name: "Retriever", icon: Search },
                        { name: "Critic", icon: ShieldAlert },
                        { name: "Query rewriter", icon: RefreshCw },
                        { name: "Responder", icon: MessageSquare },
                        { name: "Report agent", icon: FileText },
                      ].map((agent, i) => (
                        <div key={i} className="flex items-center gap-3 px-3 py-2 rounded-md bg-muted/50 border border-transparent text-xs text-foreground font-medium">
                          <agent.icon className="w-4 h-4 text-muted-foreground" />
                          {agent.name}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div>
                    <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-4">SOURCES</div>
                    {step >= 5 ? (
                      <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="flex items-center gap-2 text-xs p-3 rounded-md bg-card border border-border text-foreground shadow-sm">
                        <GitBranch className="w-4 h-4 text-muted-foreground" />
                        <span className="truncate">langchain-ai/langgraph</span>
                      </motion.div>
                    ) : (
                      <div className="text-xs text-muted-foreground">No sources yet</div>
                    )}
                  </div>
                </div>

                {/* Middle Chat Area */}
                <div className="flex-1 flex flex-col bg-background">
                  <div className="flex-1 p-6 flex flex-col justify-center items-center relative">
                    {step === 3 && (
                      <div className="flex flex-col items-center justify-center h-full text-muted-foreground opacity-90">
                        <Bot className="w-12 h-12 mb-4" />
                        <h2 className="text-lg font-heading font-semibold text-foreground">Ask anything</h2>
                        <p className="text-sm mt-1">Paste a link or upload a file to get started</p>
                      </div>
                    )}

                    {/* Chat Bubbles (Step 5) */}
                    {step >= 5 && (
                      <div className="absolute inset-0 p-8 flex flex-col gap-8">
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="self-end max-w-[80%] bg-primary text-primary-foreground rounded-2xl rounded-tr-sm px-5 py-3.5 text-sm shadow-sm">
                          Explain the core architecture of LangGraph.
                        </motion.div>

                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }} className="self-start max-w-[85%] flex gap-4">
                          <div className="w-8 h-8 rounded-full bg-primary/10 text-primary flex items-center justify-center shrink-0 mt-1">
                            <Sparkles className="w-4 h-4" />
                          </div>
                          <div className="bg-card border border-border rounded-2xl rounded-tl-sm px-5 py-4 text-sm text-foreground space-y-4 shadow-sm leading-relaxed">
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1 }}>
                              LangGraph models workflows as state machines using graphs.
                            </motion.div>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 2 }}>
                              Unlike standard DAGs, it inherently supports cycles, making it perfect for agentic loops where an agent needs to evaluate its own output and self-correct before continuing.
                            </motion.div>
                            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 3 }} className="inline-flex items-center gap-1.5 mt-2 px-2 py-1 rounded-md bg-muted border border-border text-[11px] text-muted-foreground font-medium">
                              <GitBranch className="w-3.5 h-3.5" /> README.md
                            </motion.div>
                          </div>
                        </motion.div>
                      </div>
                    )}
                  </div>

                  {/* Input Bar */}
                  <div className="p-4 bg-background">
                    <div className="w-full bg-background border border-border rounded-xl p-3 flex items-center gap-3 shadow-sm focus-within:ring-1 focus-within:ring-primary">
                      <motion.div 
                        initial={{ width: 0, opacity: 0 }} 
                        animate={{ width: step === 4 ? "auto" : step === 5 ? "auto" : 0, opacity: step >= 4 ? 1 : 0 }} 
                        className="flex-1 text-sm text-foreground flex items-center overflow-hidden"
                      >
                        <span className="whitespace-nowrap overflow-hidden">
                          {step === 4 ? "https://github.com/langchain-ai/langgraph" : "Explain the core architecture of LangGraph."}
                        </span>
                        <motion.div className="w-0.5 h-4 bg-foreground ml-1" animate={{ opacity: [1, 0] }} transition={{ repeat: Infinity, duration: 0.8 }} />
                      </motion.div>
                      {step < 4 && <div className="flex-1 text-sm text-muted-foreground px-2">Ask anything or paste a URL to ingest...</div>}
                      
                      <Paperclip className="w-4 h-4 text-muted-foreground" />
                      <div className="w-9 h-9 rounded-lg bg-primary text-primary-foreground flex items-center justify-center">
                        <Send className="w-4 h-4" />
                      </div>
                    </div>
                  </div>
                </div>

                {/* Right Sidebar */}
                <div className="w-[300px] border-l border-border p-5 flex flex-col gap-6 bg-background/50 shrink-0">
                  <div>
                    <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-4">EVALUATION</div>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
                        <div className="text-2xl font-medium mb-1 text-foreground">
                          {step >= 5 ? <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 3.5 }}>0.98</motion.span> : <span className="text-muted-foreground/30">—</span>}
                        </div>
                        <div className="text-[11px] text-muted-foreground">Faithfulness</div>
                      </div>
                      <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
                        <div className="text-2xl font-medium mb-1 text-foreground">
                          {step >= 5 ? <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 3.8 }}>0.95</motion.span> : <span className="text-muted-foreground/30">—</span>}
                        </div>
                        <div className="text-[11px] text-muted-foreground">Confidence</div>
                      </div>
                      <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
                        <div className="text-2xl font-medium mb-1 text-foreground">
                          {step >= 5 ? <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 4 }}>1</motion.span> : <span className="text-muted-foreground/30">0</span>}
                        </div>
                        <div className="text-[11px] text-muted-foreground">Retries</div>
                      </div>
                      <div className="bg-card border border-border rounded-xl p-4 shadow-sm">
                        <div className="text-2xl font-medium mb-1 text-foreground">
                          {step >= 5 ? <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 4.2 }}>3</motion.span> : <span className="text-muted-foreground/30">0</span>}
                        </div>
                        <div className="text-[11px] text-muted-foreground">Sources</div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider mb-4">RETRIEVAL</div>
                    <div className="bg-card border border-border rounded-xl p-4 text-xs text-muted-foreground min-h-[100px] shadow-sm">
                      {step >= 5 ? (
                        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 1.5 }} className="space-y-3">
                          <div className="flex items-center gap-2 text-foreground"><CheckCircle2 className="w-4 h-4 text-green-500" /> Retrieved 5 chunks</div>
                          <div className="flex items-center gap-2 text-foreground"><CheckCircle2 className="w-4 h-4 text-green-500" /> Critic passed (score: 0.92)</div>
                        </motion.div>
                      ) : (
                        <span className="text-muted-foreground/50">No retrieval yet</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Bottom Timeline Bar */}
              <div className="h-10 border-t border-border bg-background px-6 flex items-center text-[11px] font-medium text-muted-foreground uppercase tracking-wider shrink-0">
                SELF-HEALING TIMELINE
                <div className="ml-6 normal-case tracking-normal text-muted-foreground flex items-center gap-2">
                    {step === 4 && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-amber-500"><RefreshCw className="w-3.5 h-3.5 animate-spin" /> Ingesting langchain-ai/langgraph...</motion.div>}
                    {step >= 5 && <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex items-center gap-2 text-green-500"><CheckCircle2 className="w-3.5 h-3.5" /> Processed query successfully</motion.div>}
                    {step < 4 && "Agent events will appear here during processing"}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
