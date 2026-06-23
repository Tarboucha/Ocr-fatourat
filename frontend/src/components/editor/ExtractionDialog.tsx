import { useState } from "react";
import { Download, FileJson, Loader2 } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import {
  downloadExtraction,
  useExtract,
  useExtractions,
  useExtractors,
} from "@/hooks/useExtract";
import type { Extraction } from "@/types";

export function ExtractionDialog({ documentId }: { documentId: number }) {
  const { data: extractors } = useExtractors();
  const { data: history } = useExtractions(documentId);
  const { run, isRunning } = useExtract(documentId);
  const [extractor, setExtractor] = useState("heuristic");
  const [viewId, setViewId] = useState<number | null>(null);

  const selected = history?.find((e) => e.id === viewId) ?? history?.[0] ?? null;

  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button variant="outline" size="sm">
          <FileJson className="size-4" />
          Extract invoice
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-3xl">
        <DialogHeader>
          <DialogTitle>Invoice extraction</DialogTitle>
        </DialogHeader>

        <div className="flex items-center gap-2">
          <Select value={extractor} onValueChange={setExtractor}>
            <SelectTrigger className="h-9 w-44 text-sm">
              <SelectValue placeholder="Extractor" />
            </SelectTrigger>
            <SelectContent>
              {(extractors ?? []).map((e) => (
                <SelectItem key={e.name} value={e.name} className="text-sm">
                  {e.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button onClick={() => run(extractor)} disabled={isRunning} size="sm">
            {isRunning ? <Loader2 className="size-4 animate-spin" /> : null}
            {isRunning ? "Extracting…" : "Run extraction"}
          </Button>
        </div>

        <div className="grid grid-cols-[200px_1fr] gap-3">
          {/* History (A/B across extractors) */}
          <ul className="max-h-80 space-y-1 overflow-y-auto border-r pr-2">
            {(history ?? []).length === 0 && (
              <li className="text-sm text-muted-foreground">No runs yet.</li>
            )}
            {(history ?? []).map((e) => (
              <li key={e.id}>
                <button
                  onClick={() => setViewId(e.id)}
                  className={cn(
                    "w-full rounded-md p-2 text-left text-sm",
                    (selected?.id === e.id) ? "bg-accent" : "hover:bg-accent/50"
                  )}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">{e.extractor}</span>
                    <StatusBadge e={e} />
                  </div>
                  <span className="text-xs text-muted-foreground">
                    {new Date(e.created_at).toLocaleTimeString()}
                  </span>
                </button>
              </li>
            ))}
          </ul>

          {/* Result viewer */}
          <div className="min-w-0">
            {selected ? (
              <>
                <div className="mb-2 flex items-center justify-between">
                  <StatusBadge e={selected} />
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={!selected.data}
                    onClick={() => downloadExtraction(selected)}
                  >
                    <Download className="size-4" />
                    Download JSON
                  </Button>
                </div>
                <pre className="max-h-72 overflow-auto rounded-md bg-muted p-3 font-mono text-xs">
                  {selected.data
                    ? JSON.stringify(selected.data, null, 2)
                    : selected.error || "No data yet."}
                </pre>
              </>
            ) : (
              <p className="text-sm text-muted-foreground">
                Run an extractor to produce structured JSON.
              </p>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function StatusBadge({ e }: { e: Extraction }) {
  if (e.status === "failed") return <Badge variant="destructive">failed</Badge>;
  if (e.status !== "done") return <Badge variant="secondary">{e.status}</Badge>;
  return e.needs_review ? (
    <Badge variant="secondary">needs review</Badge>
  ) : (
    <Badge>ok</Badge>
  );
}
