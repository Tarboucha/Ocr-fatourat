import { useNavigate } from "react-router-dom";
import { TopBar } from "../components/TopBar";
import { UploadDropzone } from "../components/UploadDropzone";
import { useDeleteDocument, useDocuments } from "../hooks/useDocuments";

export function DocumentsPage() {
  const navigate = useNavigate();
  const { data: docs, isLoading } = useDocuments();
  const del = useDeleteDocument();

  return (
    <div className="flex h-full flex-col">
      <TopBar />
      <main className="mx-auto w-full max-w-4xl flex-1 space-y-6 p-6">
        <UploadDropzone />

        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">
            Your documents
          </h2>
          {isLoading ? (
            <p className="text-slate-500">Loading…</p>
          ) : !docs || docs.length === 0 ? (
            <p className="text-slate-500">No documents yet. Upload one to get started.</p>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {docs.map((doc) => (
                <li
                  key={doc.id}
                  className="flex items-center justify-between rounded-lg border border-slate-200 bg-white p-4 shadow-sm"
                >
                  <button
                    onClick={() => navigate(`/documents/${doc.id}`)}
                    className="min-w-0 flex-1 text-left"
                  >
                    <p className="truncate font-medium text-slate-800">{doc.filename}</p>
                    <p className="text-sm text-slate-500">
                      {doc.width}×{doc.height} · {new Date(doc.created_at).toLocaleString()}
                    </p>
                  </button>
                  <button
                    onClick={() => {
                      if (confirm(`Delete "${doc.filename}"?`)) del.mutate(doc.id);
                    }}
                    className="ml-3 rounded-md px-2 py-1 text-sm text-red-600 hover:bg-red-50"
                  >
                    Delete
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
      </main>
    </div>
  );
}
