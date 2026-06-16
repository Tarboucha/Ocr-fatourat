export interface User {
  id: number;
  email: string;
  created_at: string;
}

export interface Document {
  id: number;
  filename: string;
  mime_type: string;
  width: number;
  height: number;
  status: string;
  created_at: string;
}

export type BoxSource = "manual" | "ocr";

export interface Box {
  id: number;
  document_id: number;
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
