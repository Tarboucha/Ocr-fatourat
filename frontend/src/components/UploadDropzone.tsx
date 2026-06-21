import { useRef, useState } from "react";
import { Loader2, UploadCloud } from "lucide-react";
import { toast } from "sonner";

import { cn } from "@/lib/utils";
import { useUploadDocument } from "@/hooks/useDocuments";

export function UploadDropzone() {
  const upload = useUploadDocument();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    upload.mutate(files[0], {
      onSuccess: (doc) => toast.success(`Uploaded “${doc.filename}”`),
      onError: (err) =>
        toast.error(err instanceof Error ? err.message : "Upload failed"),
    });
  }

  return (
    <div
      onDragOver={(e) => {
        e.preventDefault();
        setDragOver(true);
      }}
      onDragLeave={() => setDragOver(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragOver(false);
        handleFiles(e.dataTransfer.files);
      }}
      onClick={() => inputRef.current?.click()}
      className={cn(
        "flex cursor-pointer flex-col items-center justify-center rounded-lg border border-dashed p-10 text-center transition-colors",
        dragOver
          ? "border-primary bg-primary/5"
          : "border-border bg-card hover:border-primary/50 hover:bg-accent/40"
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf,image/*"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <span className="mb-3 flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        {upload.isPending ? (
          <Loader2 className="size-5 animate-spin" />
        ) : (
          <UploadCloud className="size-5" />
        )}
      </span>
      <p className="font-medium">
        {upload.isPending ? "Uploading…" : "Drop a PDF or image, or click to upload"}
      </p>
      <p className="mt-1 text-sm text-muted-foreground">
        PDF, PNG, JPEG, WebP, BMP, TIFF
      </p>
    </div>
  );
}
