export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Document {
  id: number;
  filename: string;
  mime_type: string;
  page_count: number;
  status: string;
  created_at: string;
}

export interface Page {
  id: number;
  document_id: number;
  page_number: number;
  width: number;
  height: number;
}

export type BoxSource = "manual" | "ocr";

export interface Box {
  id: number;
  page_id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  text: string | null;
  source: BoxSource;
  confidence: number | null;
  order: number;
  created_at: string;
  updated_at: string;
}

/** A box as held in the editor before/while saving. `id` may be a temporary
 *  client id (negative) for boxes not yet persisted. */
export interface EditorBox {
  id: number;
  x: number;
  y: number;
  w: number;
  h: number;
  text: string | null;
  source: BoxSource;
  confidence: number | null;
  order: number;
}

export interface BoxInput {
  id?: number;
  x: number;
  y: number;
  w: number;
  h: number;
  text: string | null;
  source: BoxSource;
  confidence: number | null;
  order: number;
}

export interface PipelineInfo {
  name: string;
  description: string;
  supports_region: boolean;
  languages: string[];
}

export type OcrJobStatus = "queued" | "processing" | "done" | "failed";

export interface OcrJob {
  id: number;
  page_id: number;
  kind: "page" | "region";
  pipeline: string;
  status: OcrJobStatus;
  error: string | null;
  box_id: number | null;
  result_text: string | null;
  result_confidence: number | null;
  box_count: number | null;
  created_at: string;
}
