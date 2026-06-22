import { ScanSearch, TextSelect, Trash2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { cn } from "@/lib/utils";
import { useEditorStore } from "@/stores/editorStore";
import type { EditorBox } from "@/types";

interface Props {
  onSave: () => void;
  onRunOcr: () => void;
  onRunRegion: (box: EditorBox) => void;
  saving: boolean;
  runningOcr: boolean;
  regionSupported: boolean;
}

export function BoxSidebar({
  onSave,
  onRunOcr,
  onRunRegion,
  saving,
  runningOcr,
  regionSupported,
}: Props) {
  const { boxes, selectedId, dirty, select, updateBox, removeBox } = useEditorStore();
  const selected = boxes.find((b) => b.id === selectedId) ?? null;

  return (
    <aside className="flex w-80 shrink-0 flex-col border-l bg-background">
      <div className="space-y-2 border-b p-3">
        <Button onClick={onSave} disabled={saving || !dirty} className="w-full">
          {saving ? "Saving…" : dirty ? "Save changes" : "Saved"}
        </Button>
        <Button
          variant="outline"
          onClick={onRunOcr}
          disabled={runningOcr}
          className="w-full"
        >
          <ScanSearch className="size-4" />
          {runningOcr ? "Running OCR…" : "Run page OCR"}
        </Button>
        {regionSupported && selected && (
          <Button
            variant="outline"
            onClick={() => onRunRegion(selected)}
            disabled={runningOcr}
            className="w-full"
          >
            <TextSelect className="size-4" />
            OCR selected box
          </Button>
        )}
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <h3 className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
          Boxes ({boxes.length})
        </h3>

        {boxes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            Switch to the Draw tool and drag on the image to create a box.
          </p>
        ) : (
          <ul className="space-y-2">
            {boxes.map((box) => (
              <li
                key={box.id}
                onClick={() => select(box.id)}
                className={cn(
                  "cursor-pointer rounded-md border p-2 transition-colors",
                  box.id === selectedId
                    ? "border-primary bg-primary/5"
                    : "hover:bg-accent/50"
                )}
              >
                <div className="mb-1 flex items-center justify-between">
                  <Badge variant={box.source === "ocr" ? "default" : "secondary"}>
                    {box.source}
                    {box.confidence != null && ` · ${Math.round(box.confidence * 100)}%`}
                  </Badge>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="size-7 text-muted-foreground hover:text-destructive"
                    onClick={(e) => {
                      e.stopPropagation();
                      removeBox(box.id);
                    }}
                  >
                    <Trash2 className="size-3.5" />
                  </Button>
                </div>
                <Textarea
                  value={box.text ?? ""}
                  placeholder="(text)"
                  onChange={(e) => updateBox(box.id, { text: e.target.value })}
                  onClick={(e) => e.stopPropagation()}
                  rows={2}
                  className="resize-none text-sm"
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
