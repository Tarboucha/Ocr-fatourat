import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

import { api, ApiError } from "../lib/api";
import type { OcrJob, PipelineInfo } from "../types";

export function usePipelines() {
  return useQuery({
    queryKey: ["ocr-pipelines"],
    queryFn: () => api.get<PipelineInfo[]>("/ocr/pipelines"),
    staleTime: 5 * 60_000,
  });
}

interface RegionArgs {
  x: number;
  y: number;
  w: number;
  h: number;
  box_id?: number;
}

/** Drives an OCR run for a page: enqueue → poll the job → on done, refresh boxes.
 *  Status is read from the DB-backed OcrJob (ownership-checked), not Celery. */
export function useOcr(pageId: number) {
  const qc = useQueryClient();
  const [jobId, setJobId] = useState<number | null>(null);

  const job = useQuery({
    queryKey: ["ocr-job", jobId],
    queryFn: () => api.get<OcrJob>(`/ocr/jobs/${jobId}`),
    enabled: jobId != null,
    refetchInterval: (q) => {
      const s = q.state.data?.status;
      return s === "queued" || s === "processing" ? 1200 : false;
    },
  });

  useEffect(() => {
    const data = job.data;
    if (!data) return;
    if (data.status === "done") {
      qc.invalidateQueries({ queryKey: ["pages", pageId, "boxes"] });
      toast.success(
        data.kind === "page"
          ? `OCR complete — ${data.box_count ?? 0} region(s)`
          : "Region OCR complete"
      );
      setJobId(null);
    } else if (data.status === "failed") {
      toast.error(data.error || "OCR failed");
      setJobId(null);
    }
  }, [job.data, pageId, qc]);

  async function runPage(pipeline: string) {
    try {
      const created = await api.post<OcrJob>(`/pages/${pageId}/ocr`, { pipeline });
      setJobId(created.id);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        toast.info("An OCR run is already in progress");
      } else {
        toast.error(err instanceof Error ? err.message : "Could not start OCR");
      }
    }
  }

  async function runRegion(pipeline: string, region: RegionArgs) {
    try {
      const created = await api.post<OcrJob>(`/pages/${pageId}/ocr/region`, {
        ...region,
        pipeline,
      });
      setJobId(created.id);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "Could not start region OCR");
    }
  }

  const isRunning =
    jobId != null &&
    (job.data?.status === "queued" || job.data?.status === "processing" || job.isLoading);

  return { runPage, runRegion, isRunning, status: job.data?.status ?? null };
}
