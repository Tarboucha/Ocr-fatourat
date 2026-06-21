import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FileText, MoreVertical, Trash2 } from "lucide-react";
import { toast } from "sonner";

import { AppShell } from "@/components/layout/AppShell";
import { UploadDropzone } from "@/components/UploadDropzone";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "@/components/ui/alert-dialog";
import { useDeleteDocument, useDocuments } from "@/hooks/useDocuments";
import type { Document } from "@/types";

export function DocumentsPage() {
  const navigate = useNavigate();
  const { data: docs, isLoading } = useDocuments();
  const del = useDeleteDocument();
  const [pendingDelete, setPendingDelete] = useState<Document | null>(null);

  function confirmDelete() {
    if (!pendingDelete) return;
    const target = pendingDelete;
    del.mutate(target.id, {
      onSuccess: () => toast.success(`Deleted “${target.filename}”`),
      onError: (err) =>
        toast.error(err instanceof Error ? err.message : "Delete failed"),
    });
    setPendingDelete(null);
  }

  return (
    <AppShell>
      <div className="mx-auto w-full max-w-5xl space-y-8 p-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Documents</h1>
          <p className="text-sm text-muted-foreground">
            Upload a PDF or image to start annotating.
          </p>
        </div>

        <UploadDropzone />

        <section className="space-y-3">
          <h2 className="text-sm font-medium text-muted-foreground">
            Your documents
          </h2>

          {isLoading ? (
            <p className="text-sm text-muted-foreground">Loading…</p>
          ) : !docs || docs.length === 0 ? (
            <Card className="flex flex-col items-center justify-center gap-1 p-10 text-center">
              <FileText className="size-6 text-muted-foreground" />
              <p className="font-medium">No documents yet</p>
              <p className="text-sm text-muted-foreground">
                Upload your first document above.
              </p>
            </Card>
          ) : (
            <ul className="grid grid-cols-1 gap-3 sm:grid-cols-2">
              {docs.map((doc) => (
                <li key={doc.id}>
                  <Card className="flex items-center gap-3 p-4 transition-colors hover:bg-accent/40">
                    <span className="flex size-10 shrink-0 items-center justify-center rounded-md bg-muted text-muted-foreground">
                      <FileText className="size-5" />
                    </span>
                    <button
                      onClick={() => navigate(`/documents/${doc.id}`)}
                      className="min-w-0 flex-1 text-left"
                    >
                      <p className="truncate font-medium">{doc.filename}</p>
                      <span className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <Badge variant="secondary">
                          {doc.page_count}{" "}
                          {doc.page_count === 1 ? "page" : "pages"}
                        </Badge>
                        <span>{new Date(doc.created_at).toLocaleDateString()}</span>
                      </span>
                    </button>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="icon" className="shrink-0">
                          <MoreVertical className="size-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem
                          onClick={() => navigate(`/documents/${doc.id}`)}
                        >
                          Open
                        </DropdownMenuItem>
                        <DropdownMenuItem
                          className="text-destructive focus:text-destructive"
                          onClick={() => setPendingDelete(doc)}
                        >
                          <Trash2 className="size-4" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </Card>
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>

      <AlertDialog
        open={pendingDelete !== null}
        onOpenChange={(open) => !open && setPendingDelete(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete document?</AlertDialogTitle>
            <AlertDialogDescription>
              “{pendingDelete?.filename}” and all its pages and boxes will be
              permanently removed. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={confirmDelete}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </AppShell>
  );
}
