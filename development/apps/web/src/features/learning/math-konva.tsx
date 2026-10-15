"use client";
import { Stage, Layer, Rect, Circle, Line, Text, Wedge } from "react-konva";
import type { MathEngineProps } from "./math-activity";
const ink = "#263e65", blue = "#345c9c", pale = "#e5edf8";
export default function PrimaryMath({ template, parameters: p, width, height, onChange }: MathEngineProps) {
  const w = 600, h = 300, compact = template === "fraction_circle" || template === "shape_explorer";
  const scale = Math.min(width / (compact ? 300 : w), height / h), offsetX=(width-w*scale)/2, offsetY=(height-h*scale)/2;
  const children = [];
  if (template === "counting_groups") {
    for (let i = 0; i < Number(p.count); i++) {
      const group = Math.floor(i / Number(p.groupSize));
      children.push(<Circle key={i} x={40 + (i % 10) * 57} y={65 + Math.floor(i / 10) * 55} radius={17} listening={false} fill={[blue,"#a0461b","#2f7960","#8155a2"][group % 4]} />);
    }
    children.push(<Text listening={false} key="caption" x={20} y={265} text={`${p.count} objects · groups of ${p.groupSize}`} fontSize={18} fill={ink} />);
  } else if (template === "fraction_bar") {
    const parts = Number(p.denominator), unit = 540 / parts;
    for (let i = 0; i < parts; i++) children.push(<Rect key={i} x={30+i*unit} y={100} width={unit} height={80} stroke="white" strokeWidth={2} fill={i < Number(p.numerator) ? blue : pale} preventDefault={false} onPointerClick={() => onChange("numerator", Number(p.numerator) === i+1 ? 0 : i+1)} />);
    children.push(<Rect key="outline" x={30} y={100} width={540} height={80} stroke={blue} strokeWidth={2} listening={false} />);
    children.push(<Text listening={false} key="fraction" x={230} y={220} width={140} align="center" text={`${p.numerator} / ${p.denominator}`} fontSize={25} fill={ink} />);
  } else if (template === "fraction_circle") {
    const parts = Number(p.denominator);
    for (let i = 0; i < parts; i++) children.push(<Wedge key={i} x={300} y={140} radius={105} angle={360/parts} rotation={i*360/parts-90} fill={i < Number(p.numerator) ? blue : pale} stroke="white" strokeWidth={2} preventDefault={false} onPointerClick={() => onChange("numerator", i+1)} />);
    children.push(<Text listening={false} key="fraction" x={230} y={260} width={140} align="center" text={`${p.numerator} / ${p.denominator}`} fontSize={22} fill={ink} />);
  } else if (template === "shape_explorer") {
    const a = Number(p.width)*26, b=Number(p.height)*26;
    if (p.shape === "circle") children.push(<Circle listening={false} key="shape" x={300} y={150} radius={Number(p.width)*15} fill={pale} stroke={blue} strokeWidth={3} />);
    else if (p.shape === "triangle") children.push(<Line listening={false} key="shape" points={[300-a/2,150+b/2,300+a/2,150+b/2,300,150-b/2]} closed fill={pale} stroke={blue} strokeWidth={3} />);
    else children.push(<Rect listening={false} key="shape" x={300-a/2} y={150-b/2} width={a} height={b} fill={pale} stroke={blue} strokeWidth={3} />);
  } else if (template === "number_line") {
    const start=Number(p.start), end=Number(p.end), map=(v:number)=>40+(v-start)/(end-start)*520;
    children.push(<Line listening={false} key="axis" points={[40,150,560,150]} stroke={ink} strokeWidth={3} />);
    for (let i=start;i<=end;i++) if (end-start<=20 || i%2===0) children.push(<Line listening={false} key={`tick-${i}`} points={[map(i),143,map(i),157]} stroke={ink} />,
      <Text listening={false} key={`label-${i}`} x={map(i)-15} y={175} width={30} align="center" text={String(i)} fill={ink} fontSize={14} />);
    children.push(<Circle key="point" x={map(Number(p.value))} y={150} radius={12} fill={blue} draggable dragBoundFunc={position => ({x:Math.min(560*scale+offsetX,Math.max(40*scale+offsetX,position.x)),y:150*scale+offsetY})} onDragEnd={event=>onChange("value",Math.round(start+(event.target.x()-40)/520*(end-start)))} />);
  } else if (template === "ruler_measurement") {
    children.push(<Rect listening={false} key="ruler" x={40} y={160} width={520} height={55} fill="#fff1c8" stroke={ink} />);
    for(let i=0;i<=10;i++) children.push(<Line listening={false} key={`tick-${i}`} points={[40+i*52,160,40+i*52,178]} stroke={ink} />,<Text listening={false} key={`n-${i}`} x={30+i*52} y={187} text={String(i)} fontSize={14} fill={ink} />);
    children.push(<Line listening={false} key="length" points={[40,125,40+Number(p.length)*52,125]} stroke={blue} strokeWidth={9} />,<Circle key="end" x={40+Number(p.length)*52} y={125} radius={12} fill={blue} draggable dragBoundFunc={position=>({x:Math.max(40*scale+offsetX,Math.min(560*scale+offsetX,position.x)),y:125*scale+offsetY})} onDragEnd={event=>onChange("length",Math.round((event.target.x()-40)/52*2)/2)} />);
  }
  return <Stage preventDefault={false} width={width} height={height}><Layer x={offsetX} y={offsetY} scaleX={scale} scaleY={scale}>{children}</Layer></Stage>;
}
