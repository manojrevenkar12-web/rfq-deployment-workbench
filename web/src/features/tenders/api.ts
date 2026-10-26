import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "../../shared/api/client";
import type { Review, TenderAnalysis, TenderRow, Verdict } from "../../shared/api/types";
import { customerPath } from "../customer/api";

const tenderPath = (cid: string, tid: string) => `${customerPath(cid)}/tenders/${encodeURIComponent(tid)}`;

export const useTenders = (cid: string) =>
  useQuery({
    queryKey: ["tenders", cid],
    queryFn: () => api.get<TenderRow[]>(`${customerPath(cid)}/tenders`),
  });

export const useTender = (cid: string, tid: string) =>
  useQuery({ queryKey: ["tender", cid, tid], queryFn: () => api.get<TenderAnalysis>(tenderPath(cid, tid)) });

export const useLetter = (cid: string, tid: string, enabled: boolean) =>
  useQuery({
    queryKey: ["letter", cid, tid],
    queryFn: () => api.text(`${tenderPath(cid, tid)}/letter`),
    enabled,
  });

export async function downloadMatrix(cid: string, tid: string) {
  const blob = await api.blob(`${tenderPath(cid, tid)}/compliance.xlsx`);
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${tid}-compliance.xlsx`;
  a.click();
  URL.revokeObjectURL(url);
}

export function useReview(cid: string, tid: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (r: { rid: string; verdict: Verdict; reviewer: string; comment?: string }) =>
      api.post<Review>(`${tenderPath(cid, tid)}/requirements/${encodeURIComponent(r.rid)}/review`, {
        verdict: r.verdict,
        reviewer: r.reviewer,
        comment: r.comment ?? "",
      }),
    onSuccess: (review) => {
      qc.setQueryData<TenderAnalysis>(["tender", cid, tid], (t) =>
        t
          ? {
              ...t,
              reviews: [...(t.reviews ?? []).filter((x) => x.requirement !== review.requirement), review],
            }
          : t,
      );
      void qc.invalidateQueries({ queryKey: ["tenders", cid] });
      void qc.invalidateQueries({ queryKey: ["portfolio"] });
    },
  });
}

export function useInbox(cid: string) {
  return useMutation({
    mutationFn: (files: File[]) => {
      const form = new FormData();
      for (const f of files) form.append("files", f, f.name);
      return api.upload<TenderAnalysis>(`${customerPath(cid)}/inbox`, form);
    },
  });
}

const REVIEWER_KEY = "rdw.reviewer";

export const reviewerName = {
  get(): string {
    try {
      return localStorage.getItem(REVIEWER_KEY) ?? "";
    } catch {
      return "";
    }
  },
  set(name: string) {
    try {
      localStorage.setItem(REVIEWER_KEY, name);
    } catch {
      /* not kept: asked again next time */
    }
  },
};
