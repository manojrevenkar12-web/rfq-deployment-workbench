import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../shared/api/client";
import type { Decision, Deployment, SteerCo } from "../../shared/api/types";

const base = (cid: string) => `/api/customers/${encodeURIComponent(cid)}`;

export const customerPath = base;

export const useDeployment = (cid: string) =>
  useQuery({ queryKey: ["customer", cid], queryFn: () => api.get<Deployment>(base(cid)) });

export const useSteerCo = (cid: string, enabled: boolean) =>
  useQuery({ queryKey: ["steerco", cid], queryFn: () => api.get<SteerCo>(`${base(cid)}/steerco`), enabled });

export function useRecordDecision(cid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { decision: string; by: string }) =>
      api.post<Decision>(`${base(cid)}/decisions`, body),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["customer", cid] });
      void qc.invalidateQueries({ queryKey: ["steerco", cid] });
    },
  });
}
