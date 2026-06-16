import { useEffect, useState } from "react";
import { api } from "../lib/api";

/** Loads the document image into an HTMLImageElement for Konva.
 *  The /file endpoint requires the auth header, so we fetch a blob (the api
 *  wrapper attaches the Bearer token) and feed an object URL to an Image. */
export function useDocumentImage(docId: number) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!docId) return;
    let cancelled = false;
    let objectUrl: string | null = null;

    setImage(null);
    setError(null);

    api
      .getBlob(`/documents/${docId}/file`)
      .then((blob) => {
        if (cancelled) return;
        objectUrl = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
          if (!cancelled) setImage(img);
        };
        img.onerror = () => {
          if (!cancelled) setError("Failed to render image");
        };
        img.src = objectUrl;
      })
      .catch((err) => {
        if (!cancelled) setError(err instanceof Error ? err.message : "Failed to load image");
      });

    return () => {
      cancelled = true;
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId]);

  return { image, error };
}
