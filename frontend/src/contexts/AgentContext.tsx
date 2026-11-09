import { createContext, useContext, useMemo, useState, type ReactNode } from "react";

type AgentContextValue = {
  agentId: string;
  setAgentId: (agentId: string) => void;
};

const AgentContext = createContext<AgentContextValue | null>(null);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [agentId, setAgentId] = useState("default");
  const value = useMemo(() => ({ agentId, setAgentId }), [agentId]);
  return <AgentContext.Provider value={value}>{children}</AgentContext.Provider>;
}

export function useAgentContext() {
  const context = useContext(AgentContext);
  if (!context) throw new Error("useAgentContext must be used inside AgentProvider");
  return context;
}
