import { useQuery } from "@tanstack/react-query";

import { api } from "../../shared/api/client";
import type { Agent, AgentId, Portfolio } from "../../shared/api/types";

export const usePortfolio = () =>
  useQuery({ queryKey: ["portfolio"], queryFn: () => api.get<Portfolio>("/api/portfolio") });

export const useAgents = () =>
  useQuery({
    queryKey: ["agents"],
    queryFn: () => api.get<Record<AgentId, Agent>>("/api/agents"),
    staleTime: Infinity,
  });
