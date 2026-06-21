import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Box, BoxInput } from "../types";

export function useBoxes(pageId: number) {
  return useQuery({
    queryKey: ["pages", pageId, "boxes"],
    queryFn: () => api.get<Box[]>(`/pages/${pageId}/boxes`),
    enabled: Number.isFinite(pageId) && pageId > 0,
  });
}

export function useSaveBoxes(pageId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (boxes: BoxInput[]) =>
      api.put<Box[]>(`/pages/${pageId}/boxes`, { boxes }),
    onSuccess: (data) => {
      qc.setQueryData(["pages", pageId, "boxes"], data);
    },
  });
}

export function useRunOcr(pageId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Box[]>(`/pages/${pageId}/ocr`),
    onSuccess: (data) => {
      qc.setQueryData(["pages", pageId, "boxes"], data);
    },
  });
}
