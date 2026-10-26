import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../shared/api/client";
import type { AgentId, Assumptions, ValueCase } from "../../shared/api/types";
import { customerPath } from "../customer/api";

export type AssumptionEdits = Partial<Omit<Assumptions, "hourly_cost">> & {
  hourly_cost?: Record<string, number>;
};

/** The value case for a scope and assumptions; without either, the customer's agreed scope and assumptions. */
export const useValue = (cid: string, scope?: AgentId[], assumptions: AssumptionEdits = {}) =>
  useQuery({
    queryKey: ["value", cid, scope ? [...scope].sort() : "agreed", assumptions],
    queryFn: () => api.post<ValueCase>(`${customerPath(cid)}/value`, { scope: scope ?? null, assumptions }),
    placeholderData: keepPreviousData,
  });

export function useSaveAssumptions(cid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (a: AssumptionEdits) => api.put<Assumptions>(`${customerPath(cid)}/assumptions`, a),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["value", cid] });
      void qc.invalidateQueries({ queryKey: ["customer", cid] });
      void qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}
