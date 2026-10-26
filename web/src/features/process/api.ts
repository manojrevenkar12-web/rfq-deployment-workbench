import { useQuery } from "@tanstack/react-query";

import { ApiError, api } from "../../shared/api/client";
import type { Discovery, LiveComparison } from "../../shared/api/types";
import { customerPath } from "../customer/api";

export const useDiscovery = (cid: string) =>
  useQuery({
    queryKey: ["discovery", cid],
    queryFn: () => api.get<Discovery>(`${customerPath(cid)}/discovery`),
  });

/** The process since go-live; null for a customer that is not live yet (the API answers 404). */
export const useLive = (cid: string, enabled = true) =>
  useQuery({
    enabled,
    queryKey: ["live", cid],
    queryFn: async () => {
      try {
        return await api.get<LiveComparison>(`${customerPath(cid)}/live`);
      } catch (e) {
        if (e instanceof ApiError && e.status === 404) return null;
        throw e;
      }
    },
  });
