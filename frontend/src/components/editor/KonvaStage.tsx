import { useEffect, useRef, useState } from "react";
import { Image as KonvaImage, Layer, Stage } from "react-konva";
import type Konva from "konva";
import { useEditorStore } from "../../stores/editorStore";
import { BoxItem } from "./BoxItem";

interface Props {
  image: HTMLImageElement;
  width: number; // viewport width in px
  height: number; // viewport height in px
}

const SCALE_BY = 1.05;
const MIN_SCALE = 0.05;
const MAX_SCALE = 8;

export function KonvaStage({ image, width, height }: Props) {
  const stageRef = useRef<Konva.Stage>(null);
  const {
    tool,
    boxes,
    selectedId,
    scale,
    position,
    setScale,
    setPosition,
    select,
    addBox,
    updateBox,
  } = useEditorStore();

  // Geometry of an in-progress drawn rect (image coords), or null.
  const [draft, setDraft] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const drawStart = useRef<{ x: number; y: number } | null>(null);

  // Fit the image into the viewport on first load / image change.
  useEffect(() => {
    const fit = Math.min(width / image.width, height / image.height, 1);
    setScale(fit);
    setPosition({
      x: (width - image.width * fit) / 2,
      y: (height - image.height * fit) / 2,
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [image, width, height]);

  function relativePointer() {
    const stage = stageRef.current;
    if (!stage) return null;
    return stage.getRelativePointerPosition();
  }

  function onWheel(e: Konva.KonvaEventObject<WheelEvent>) {
    e.evt.preventDefault();
    const stage = stageRef.current;
    if (!stage) return;
    const pointer = stage.getPointerPosition();
    if (!pointer) return;

    const oldScale = scale;
    const mousePoint = {
      x: (pointer.x - position.x) / oldScale,
      y: (pointer.y - position.y) / oldScale,
    };
    const direction = e.evt.deltaY > 0 ? -1 : 1;
    let newScale = direction > 0 ? oldScale * SCALE_BY : oldScale / SCALE_BY;
    newScale = Math.max(MIN_SCALE, Math.min(MAX_SCALE, newScale));

    setScale(newScale);
    setPosition({
      x: pointer.x - mousePoint.x * newScale,
      y: pointer.y - mousePoint.y * newScale,
    });
  }

  function onMouseDown(e: Konva.KonvaEventObject<MouseEvent>) {
    if (tool === "draw") {
      const pos = relativePointer();
      if (!pos) return;
      drawStart.current = pos;
      setDraft({ x: pos.x, y: pos.y, w: 0, h: 0 });
    } else {
      // Clicking empty stage clears selection.
      if (e.target === e.target.getStage() || e.target.className === "Image") {
        select(null);
      }
    }
  }

  function onMouseMove() {
    if (tool !== "draw" || !drawStart.current) return;
    const pos = relativePointer();
    if (!pos) return;
    const s = drawStart.current;
    setDraft({
      x: Math.min(s.x, pos.x),
      y: Math.min(s.y, pos.y),
      w: Math.abs(pos.x - s.x),
      h: Math.abs(pos.y - s.y),
    });
  }

  function onMouseUp() {
    if (tool === "draw" && draft && draft.w > 3 && draft.h > 3) {
      addBox({
        x: draft.x,
        y: draft.y,
        w: draft.w,
        h: draft.h,
        text: "",
        source: "manual",
        confidence: null,
        order: boxes.length,
      });
    }
    drawStart.current = null;
    setDraft(null);
  }

  return (
    <Stage
      ref={stageRef}
      width={width}
      height={height}
      scaleX={scale}
      scaleY={scale}
      x={position.x}
      y={position.y}
      draggable={tool === "select"}
      onWheel={onWheel}
      onMouseDown={onMouseDown}
      onMouseMove={onMouseMove}
      onMouseUp={onMouseUp}
      onDragEnd={(e) => {
        // Only the stage itself panning updates position.
        if (e.target === stageRef.current) {
          setPosition({ x: e.target.x(), y: e.target.y() });
        }
      }}
      className="bg-slate-200"
    >
      <Layer>
        <KonvaImage image={image} x={0} y={0} listening={false} />
      </Layer>
      <Layer>
        {boxes.map((box) => (
          <BoxItem
            key={box.id}
            box={box}
            isSelected={box.id === selectedId}
            draggable={tool === "select"}
            onSelect={() => select(box.id)}
            onChange={(patch) => updateBox(box.id, patch)}
          />
        ))}
        {draft && (
          <BoxItem
            box={{
              id: -999999,
              ...draft,
              text: "",
              source: "manual",
              confidence: null,
              order: 0,
            }}
            isSelected={false}
            draggable={false}
            onSelect={() => {}}
            onChange={() => {}}
          />
        )}
      </Layer>
    </Stage>
  );
}
