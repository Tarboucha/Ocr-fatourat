import { useEffect, useState } from "react";
import { api } from "../lib/api";

/** Loads a page's rasterized PNG into an HTMLImageElement for Konva.
 *  The /file endpoint requires the auth header, so we fetch a blob (the api
 *  wrapper attaches the Bearer token) and feed an object URL to an Image. */
export function usePageImage(pageId: number | null) {
  const [image, setImage] = useState<HTMLImageElement | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!pageId) return;
    let cancelled = false;
    let objectUrl: string | null = null;

    setImage(null);
    setError(null);

    api
      .getBlob(`/pages/${pageId}/file`)
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
  }, [pageId]);

  return { image, error };
}
