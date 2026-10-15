"use client";
import { Coordinates, Mafs, MovablePoint, Plot, Text } from "mafs";
import { functionValue } from "./math-spec";
import type { MathEngineProps } from "./math-activity";
import "mafs/core.css";

export default function FunctionMath({ template, parameters:p, width, height, onChange }: MathEngineProps) {
  const curve = template !== "coordinate_points";
  const x=Number(p.x), y=curve ? functionValue(template,p,x) : Number(p.y);
  return <Mafs width={width} height={height} viewBox={{x:[-8,8],y:[-6,6]}} pan zoom={{min:.5,max:2}}>
    <Coordinates.Cartesian />
    {curve && <Plot.OfX y={value=>functionValue(template,p,value)} domain={[-8,8]} minSamplingDepth={4} maxSamplingDepth={10} color="#345c9c" />}
    <MovablePoint point={[x,y]} onMove={point=>{onChange("x",Math.round(point[0]*2)/2);if(!curve)onChange("y",Math.round(point[1]*2)/2);}} constrain={point=>[Math.max(curve?-5:-8,Math.min(curve?5:8,point[0])),curve?functionValue(template,p,Math.max(-5,Math.min(5,point[0]))):Math.max(-6,Math.min(6,point[1]))]} color="#a0461b" />
    <Text x={x} y={Math.max(-5.5,Math.min(5.5,y))} attach="n" size={15}>({x}, {Math.round(y*100)/100})</Text>
  </Mafs>;
}
