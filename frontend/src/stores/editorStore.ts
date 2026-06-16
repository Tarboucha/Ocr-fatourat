import { create } from "zustand";
import type { Box, EditorBox } from "../types";

export type Tool = "select" | "draw";

interface EditorState {
  tool: Tool;
  boxes: EditorBox[];
  selectedId: number | null;
  scale: number;
  /** Stage position (pan offset) in screen px. */
  position: { x: number; y: number };
  dirty: boolean;
  nextTempId: number;

  setTool: (tool: Tool) => void;
  setScale: (scale: number) => void;
  setPosition: (position: { x: number; y: number }) => void;
  select: (id: number | null) => void;

  loadBoxes: (boxes: Box[]) => void;
  addBox: (box: Omit<EditorBox, "id">) => number;
  updateBox: (id: number, patch: Partial<EditorBox>) => void;
  removeBox: (id: number) => void;
  markClean: () => void;
}

export const useEditorStore = create<EditorState>((set, get) => ({
  tool: "select",
  boxes: [],
  selectedId: null,
  scale: 1,
  position: { x: 0, y: 0 },
  dirty: false,
  nextTempId: -1,

  setTool: (tool) => set({ tool }),
  setScale: (scale) => set({ scale }),
  setPosition: (position) => set({ position }),
  select: (selectedId) => set({ selectedId }),

  loadBoxes: (boxes) =>
    set({
      boxes: boxes.map((b) => ({
        id: b.id,
        x: b.x,
        y: b.y,
        w: b.w,
        h: b.h,
        text: b.text,
        source: b.source,
        confidence: b.confidence,
        order: b.order,
      })),
      dirty: false,
      selectedId: null,
    }),

  addBox: (box) => {
    const id = get().nextTempId;
    set((s) => ({
      boxes: [...s.boxes, { ...box, id }],
      nextTempId: s.nextTempId - 1,
      selectedId: id,
      dirty: true,
    }));
    return id;
  },

  updateBox: (id, patch) =>
    set((s) => ({
      boxes: s.boxes.map((b) => (b.id === id ? { ...b, ...patch } : b)),
      dirty: true,
    })),

  removeBox: (id) =>
    set((s) => ({
      boxes: s.boxes.filter((b) => b.id !== id),
      selectedId: s.selectedId === id ? null : s.selectedId,
      dirty: true,
    })),

  markClean: () => set({ dirty: false }),
}));
