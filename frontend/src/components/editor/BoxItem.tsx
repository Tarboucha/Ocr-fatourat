import { useEffect, useRef } from "react";
import { Rect, Transformer } from "react-konva";
import type Konva from "konva";
import type { EditorBox } from "../../types";

const SOURCE_COLORS: Record<EditorBox["source"], string> = {
  manual: "#4f46e5", // indigo
  ocr: "#059669", // emerald
};

interface Props {
  box: EditorBox;
  isSelected: boolean;
  draggable: boolean;
  onSelect: () => void;
  onChange: (patch: Partial<EditorBox>) => void;
}

/** A single resizable/draggable rectangle. Geometry is in image-pixel coords;
 *  the parent Layer applies the stage scale, so we work in image units here. */
export function BoxItem({ box, isSelected, draggable, onSelect, onChange }: Props) {
  const rectRef = useRef<Konva.Rect>(null);
  const trRef = useRef<Konva.Transformer>(null);

  useEffect(() => {
    if (isSelected && trRef.current && rectRef.current) {
      trRef.current.nodes([rectRef.current]);
      trRef.current.getLayer()?.batchDraw();
    }
  }, [isSelected]);

  const color = SOURCE_COLORS[box.source];

  return (
    <>
      <Rect
        ref={rectRef}
        x={box.x}
        y={box.y}
        width={box.w}
        height={box.h}
        stroke={color}
        strokeWidth={2}
        strokeScaleEnabled={false}
        fill={color}
        opacity={isSelected ? 0.18 : 0.1}
        draggable={draggable}
        onMouseDown={onSelect}
        onTap={onSelect}
        onClick={onSelect}
        onDragEnd={(e) => onChange({ x: e.target.x(), y: e.target.y() })}
        onTransformEnd={() => {
          const node = rectRef.current;
          if (!node) return;
          const scaleX = node.scaleX();
          const scaleY = node.scaleY();
          // Bake the transform scale into width/height and reset node scale.
          const w = Math.max(4, node.width() * scaleX);
          const h = Math.max(4, node.height() * scaleY);
          node.scaleX(1);
          node.scaleY(1);
          onChange({ x: node.x(), y: node.y(), w, h });
        }}
      />
      {isSelected && draggable && (
        <Transformer
          ref={trRef}
          rotateEnabled={false}
          ignoreStroke
          boundBoxFunc={(oldBox, newBox) =>
            newBox.width < 4 || newBox.height < 4 ? oldBox : newBox
          }
        />
      )}
    </>
  );
}
