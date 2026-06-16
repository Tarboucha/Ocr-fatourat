import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { Box, BoxInput } from "../types";

export function useBoxes(docId: number) {
  return useQuery({
    queryKey: ["documents", docId, "boxes"],
    queryFn: () => api.get<Box[]>(`/documents/${docId}/boxes`),
    enabled: Number.isFinite(docId) && docId > 0,
  });
}

export function useSaveBoxes(docId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (boxes: BoxInput[]) =>
      api.put<Box[]>(`/documents/${docId}/boxes`, { boxes }),
    onSuccess: (data) => {
      qc.setQueryData(["documents", docId, "boxes"], data);
    },
  });
}

export function useRunOcr(docId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.post<Box[]>(`/documents/${docId}/ocr`),
    onSuccess: (data) => {
      qc.setQueryData(["documents", docId, "boxes"], data);
    },
  });
}
