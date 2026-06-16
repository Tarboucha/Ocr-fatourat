import { useEditorStore } from "../../stores/editorStore";

interface Props {
  onSave: () => void;
  onRunOcr: () => void;
  saving: boolean;
  runningOcr: boolean;
}

export function BoxSidebar({ onSave, onRunOcr, saving, runningOcr }: Props) {
  const { boxes, selectedId, dirty, select, updateBox, removeBox } = useEditorStore();

  return (
    <aside className="flex w-80 flex-col border-l border-slate-200 bg-white">
      <div className="space-y-2 border-b border-slate-200 p-3">
        <button
          onClick={onSave}
          disabled={saving || !dirty}
          className="w-full rounded-md bg-indigo-600 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {saving ? "Saving…" : dirty ? "Save changes" : "Saved"}
        </button>
        <button
          onClick={onRunOcr}
          disabled={runningOcr}
          className="w-full rounded-md border border-slate-300 py-2 text-sm font-medium hover:bg-slate-50 disabled:opacity-50"
        >
          {runningOcr ? "Running OCR…" : "Run OCR"}
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
          Boxes ({boxes.length})
        </h3>
        {boxes.length === 0 ? (
          <p className="text-sm text-slate-400">
            Switch to the Draw tool and drag on the image to create a box.
          </p>
        ) : (
          <ul className="space-y-2">
            {boxes.map((box) => (
              <li
                key={box.id}
                onClick={() => select(box.id)}
                className={`cursor-pointer rounded-md border p-2 ${
                  box.id === selectedId
                    ? "border-indigo-400 bg-indigo-50"
                    : "border-slate-200 hover:bg-slate-50"
                }`}
              >
                <div className="mb-1 flex items-center justify-between">
                  <span
                    className={`rounded px-1.5 py-0.5 text-[10px] font-medium uppercase ${
                      box.source === "ocr"
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-indigo-100 text-indigo-700"
                    }`}
                  >
                    {box.source}
                    {box.confidence != null && ` · ${Math.round(box.confidence * 100)}%`}
                  </span>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeBox(box.id);
                    }}
                    className="text-xs text-red-600 hover:underline"
                  >
                    remove
                  </button>
                </div>
                <textarea
                  value={box.text ?? ""}
                  placeholder="(text)"
                  onChange={(e) => updateBox(box.id, { text: e.target.value })}
                  onClick={(e) => e.stopPropagation()}
                  rows={2}
                  className="w-full resize-none rounded border border-slate-200 px-2 py-1 text-sm outline-none focus:border-indigo-400"
                />
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
