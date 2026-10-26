import { useQuery } from "@tanstack/react-query";

import { api } from "../../shared/api/client";
import type { Readiness } from "../../shared/api/types";
import { customerPath } from "../customer/api";

export const useReadiness = (cid: string) =>
  useQuery({
    queryKey: ["readiness", cid],
    queryFn: () => api.get<Readiness>(`${customerPath(cid)}/readiness`),
  });
