import { useRef, useState } from "react";
import { useUploadDocument } from "../hooks/useDocuments";

export function UploadDropzone() {
  const upload = useUploadDocument();
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    upload.mutate(files[0]);
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
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-8 text-center transition ${
        dragOver ? "border-indigo-500 bg-indigo-50" : "border-slate-300 bg-white hover:border-indigo-400"
      }`}
    >
      <input
        ref={inputRef}
        type="file"
        accept="image/*"
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
      <p className="font-medium text-slate-700">
        {upload.isPending ? "Uploading…" : "Drop an image here or click to upload"}
      </p>
      <p className="mt-1 text-sm text-slate-500">PNG, JPEG, WebP, BMP, TIFF</p>
      {upload.isError && (
        <p className="mt-2 text-sm text-red-600">
          {upload.error instanceof Error ? upload.error.message : "Upload failed"}
        </p>
      )}
    </div>
  );
}
