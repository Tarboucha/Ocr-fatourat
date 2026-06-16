import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { useParams } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { BoxSidebar } from "../components/editor/BoxSidebar";
import { KonvaStage } from "../components/editor/KonvaStage";
import { useBoxes, useRunOcr, useSaveBoxes } from "../hooks/useBoxes";
import { useDocument } from "../hooks/useDocuments";
import { useDocumentImage } from "../hooks/useDocumentImage";
import { useEditorStore } from "../stores/editorStore";
import type { BoxInput } from "../types";

export function EditorPage() {
  const { id } = useParams();
  const docId = Number(id);

  const { data: doc } = useDocument(docId);
  const { data: boxes } = useBoxes(docId);
  const { image, error: imageError } = useDocumentImage(docId);
  const saveBoxes = useSaveBoxes(docId);
  const runOcr = useRunOcr(docId);

  const { tool, setTool, scale, loadBoxes, markClean, removeBox, selectedId } = useEditorStore();

  const containerRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  // Sync fetched boxes into the editor store.
  useEffect(() => {
    if (boxes) loadBoxes(boxes);
  }, [boxes, loadBoxes]);

  // Measure the canvas viewport.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const update = () => setSize({ width: el.clientWidth, height: el.clientHeight });
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Delete key removes the selected box (when not typing in an input).
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
    saveBoxes.mutate(payload, { onSuccess: () => markClean() });
  }

  return (
    <div className="flex h-full flex-col">
      <TopBar>
        <span className="text-sm text-slate-500">{doc?.filename}</span>
      </TopBar>

      <div className="flex items-center gap-2 border-b border-slate-200 bg-white px-4 py-2">
        <ToolButton active={tool === "select"} onClick={() => setTool("select")}>
          Select / Pan
        </ToolButton>
        <ToolButton active={tool === "draw"} onClick={() => setTool("draw")}>
          Draw box
        </ToolButton>
        <span className="ml-2 text-xs text-slate-400">Zoom: {Math.round(scale * 100)}%</span>
        <span className="ml-auto text-xs text-slate-400">
          Scroll to zoom · drag to pan · Del to remove selected
        </span>
      </div>

      <div className="flex min-h-0 flex-1">
        <div ref={containerRef} className="relative min-w-0 flex-1 overflow-hidden bg-slate-200">
          {imageError ? (
            <div className="flex h-full items-center justify-center text-red-600">{imageError}</div>
          ) : !image || size.width === 0 ? (
            <div className="flex h-full items-center justify-center text-slate-500">Loading image…</div>
          ) : (
            <KonvaStage image={image} width={size.width} height={size.height} />
          )}
        </div>
        <BoxSidebar
          onSave={handleSave}
          onRunOcr={() => runOcr.mutate()}
          saving={saveBoxes.isPending}
          runningOcr={runOcr.isPending}
        />
      </div>
    </div>
  );
}

function ToolButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      onClick={onClick}
      className={`rounded-md px-3 py-1.5 text-sm font-medium ${
        active ? "bg-indigo-600 text-white" : "border border-slate-300 hover:bg-slate-50"
      }`}
    >
      {children}
    </button>
  );
}
