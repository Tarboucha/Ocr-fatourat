import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { ChevronLeft, ChevronRight, MousePointer2, SquareDashedMousePointer } from "lucide-react";
import { toast } from "sonner";

import { AppShell } from "@/components/layout/AppShell";
import { BoxSidebar } from "@/components/editor/BoxSidebar";
import { KonvaStage } from "@/components/editor/KonvaStage";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
import { useBoxes, useSaveBoxes } from "@/hooks/useBoxes";
import { useOcr, usePipelines } from "@/hooks/useOcr";
import { useDocument, usePages } from "@/hooks/useDocuments";
import { usePageImage } from "@/hooks/usePageImage";
import { useEditorStore } from "@/stores/editorStore";
import type { BoxInput, EditorBox } from "@/types";

export function EditorPage() {
  const { id } = useParams();
  const docId = Number(id);

  const { data: doc } = useDocument(docId);
  const { data: pages } = usePages(docId);

  const [pageIndex, setPageIndex] = useState(0);
  const currentPage = pages?.[pageIndex] ?? null;
  const pageId = currentPage?.id ?? 0;

  const { data: boxes } = useBoxes(pageId);
  const { image, error: imageError } = usePageImage(pageId || null);
  const saveBoxes = useSaveBoxes(pageId);

  const { data: pipelines } = usePipelines();
  const { runPage, runRegion, isRunning: ocrRunning } = useOcr(pageId);
  const [pipeline, setPipeline] = useState("rapidocr");
  useEffect(() => {
    if (pipelines && pipelines.length && !pipelines.some((p) => p.name === pipeline)) {
      setPipeline(pipelines[0].name);
    }
  }, [pipelines, pipeline]);
  const regionSupported =
    pipelines?.find((p) => p.name === pipeline)?.supports_region ?? false;

  const { tool, setTool, scale, loadBoxes, markClean, removeBox, selectedId, dirty } =
    useEditorStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    if (pages && pageIndex > pages.length - 1) setPageIndex(0);
  }, [pages, pageIndex]);

  useEffect(() => {
    if (boxes) loadBoxes(boxes);
  }, [boxes, loadBoxes]);

  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const target = e.target as HTMLElement;
      const typing = target.tagName === "INPUT" || target.tagName === "TEXTAREA";
      if (!typing && selectedId != null && (e.key === "Delete" || e.key === "Backspace")) {
        removeBox(selectedId);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, removeBox]);

  function handleSave() {
    const current = useEditorStore.getState().boxes;
    const payload: BoxInput[] = current.map((b, i) => ({
      x: b.x,
      y: b.y,
      w: b.w,
      h: b.h,
      text: b.text,
      source: b.source,
      confidence: b.confidence,
      order: i,
    }));
    saveBoxes.mutate(payload, {
      onSuccess: () => {
        markClean();
        toast.success("Boxes saved");
      },
      onError: (err) =>
        toast.error(err instanceof Error ? err.message : "Save failed"),
    });
  }

  function handleRunRegion(box: EditorBox) {
    runRegion(pipeline, {
      x: box.x,
      y: box.y,
      w: box.w,
      h: box.h,
      box_id: box.id > 0 ? box.id : undefined,
    });
  }

  function changePage(next: number) {
    if (!pages) return;
    const clamped = Math.max(0, Math.min(pages.length - 1, next));
    if (clamped === pageIndex) return;
    if (dirty && !confirm("You have unsaved changes on this page. Discard them?")) return;
    setPageIndex(clamped);
  }

  const pageCount = pages?.length ?? doc?.page_count ?? 0;
  const stageKey = useMemo(() => `page-${pageId}`, [pageId]);

  const toolbar = (
    <>
      <span className="truncate text-sm font-medium">{doc?.filename}</span>

      <Separator orientation="vertical" className="mx-1 h-6" />

      <ToggleGroup
        type="single"
        size="sm"
        variant="outline"
        value={tool}
        onValueChange={(v) => v && setTool(v as "select" | "draw")}
      >
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value="select" aria-label="Select / pan">
              <MousePointer2 className="size-4" />
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent>Select / pan</TooltipContent>
        </Tooltip>
        <Tooltip>
          <TooltipTrigger asChild>
            <ToggleGroupItem value="draw" aria-label="Draw box">
              <SquareDashedMousePointer className="size-4" />
            </ToggleGroupItem>
          </TooltipTrigger>
          <TooltipContent>Draw box</TooltipContent>
        </Tooltip>
      </ToggleGroup>

      {pageCount > 1 && (
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            onClick={() => changePage(pageIndex - 1)}
            disabled={pageIndex <= 0}
          >
            <ChevronLeft className="size-4" />
          </Button>
          <span className="min-w-20 text-center font-mono text-xs text-muted-foreground">
            {pageIndex + 1} / {pageCount}
          </span>
          <Button
            variant="outline"
            size="icon"
            className="size-8"
            onClick={() => changePage(pageIndex + 1)}
            disabled={pageIndex >= pageCount - 1}
          >
            <ChevronRight className="size-4" />
          </Button>
        </div>
      )}

      <div className="ml-auto flex items-center gap-2">
        <Select value={pipeline} onValueChange={setPipeline}>
          <SelectTrigger className="h-8 w-36 text-xs" aria-label="OCR pipeline">
            <SelectValue placeholder="Pipeline" />
          </SelectTrigger>
          <SelectContent>
            {(pipelines ?? []).map((p) => (
              <SelectItem key={p.name} value={p.name} className="text-xs">
                {p.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="font-mono text-xs text-muted-foreground">
          {Math.round(scale * 100)}%
        </span>
      </div>
    </>
  );

  return (
    <AppShell toolbar={toolbar} fill>
      <div className="flex h-full min-h-0">
        <div ref={containerRef} className="relative min-w-0 flex-1 overflow-hidden bg-muted">
          {imageError ? (
            <div className="flex h-full items-center justify-center text-destructive">
              {imageError}
            </div>
          ) : !image || size.width === 0 ? (
            <div className="flex h-full items-center justify-center text-muted-foreground">
              Loading page…
            </div>
          ) : (
            <KonvaStage key={stageKey} image={image} width={size.width} height={size.height} />
          )}
        </div>
        <BoxSidebar
          onSave={handleSave}
          onRunOcr={() => runPage(pipeline)}
          onRunRegion={handleRunRegion}
          saving={saveBoxes.isPending}
          runningOcr={ocrRunning}
          regionSupported={regionSupported}
        />
      </div>
    </AppShell>
  );
}
