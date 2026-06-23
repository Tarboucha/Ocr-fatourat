import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, API_BASE } from "../lib/api";
import { useAuthStore } from "../stores/authStore";
import type { Extraction, ExtractorInfo } from "../types";

export function useExtractors() {
  return useQuery({
    queryKey: ["extractors"],
    queryFn: () => api.get<ExtractorInfo[]>("/extract/extractors"),
    staleTime: 5 * 60_000,
  });
}

export function useExtractions(documentId: number) {
  return useQuery({
    queryKey: ["documents", documentId, "extractions"],
    queryFn: () => api.get<Extraction[]>(`/documents/${documentId}/extractions`),
    enabled: Number.isFinite(documentId) && documentId > 0,
  });
}

/** Enqueue an extraction and poll it to completion. */
export function useExtract(documentId: number) {
  const qc = useQueryClient();
  const [extractionId, setExtractionId] = useState<number | null>(null);

  const extraction = useQuery({
    queryKey: ["extraction", extractionId],
    queryFn: () => api.get<Extraction>(`/extractions/${extractionId}`),
    enabled: extractionId != null,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "queued" || s === "processing" ? 1500 : false;
    },
  });

  useEffect(() => {
    const data = extraction.data;
    if (!data) return;
    if (data.status === "done") {
      qc.invalidateQueries({ queryKey: ["documents", documentId, "extractions"] });
      toast[data.needs_review ? "warning" : "success"](
        data.needs_review ? "Extraction done — needs review" : "Extraction complete"
      );
      setExtractionId(null);
    } else if (data.status === "failed") {
      toast.error(data.error || "Extraction failed");
      setExtractionId(null);
    }
  }, [extraction.data, documentId, qc]);

  async function run(extractor: string) {
    try {
      const created = await api.post<Extraction>(`/documents/${documentId}/extract`, {
        extractor,
      });
      setExtractionId(created.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start extraction");
    }
  }

  const isRunning =
    extractionId != null &&
    (extraction.data?.status === "queued" ||
      extraction.data?.status === "processing" ||
      extraction.isLoading);

  return { run, isRunning };
}

/** Download an extraction's JSON via the authed export endpoint. */
export async function downloadExtraction(extraction: Extraction) {
  const { token } = useAuthStore.getState();
  const res = await fetch(`${API_BASE}/extractions/${extraction.id}/export`, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!res.ok) {
    toast.error("Download failed");
    return;
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `invoice-${extraction.document_id}-${extraction.extractor}.json`;
  a.click();
  URL.revokeObjectURL(url);
}
