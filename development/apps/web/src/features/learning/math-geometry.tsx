"use client";
import JXG from "jsxgraph";
import { useEffect, useRef } from "react";
import type { MathEngineProps } from "./math-activity";

export default function GeometryMath({ template, parameters:p, width, height, onChange }: MathEngineProps) {
  const host=useRef<HTMLDivElement>(null), board=useRef<JXG.Board | null>(null), points=useRef<Record<string,JXG.Point>>({});
  const latest=useRef({p,onChange});latest.current={p,onChange};
  useEffect(()=>{
    const element=host.current;
    if(!element)return;
    // JSXGraph's shipped types omit the documented keyboard option.
    const options: Partial<JXG.BoardAttributes> & { keyboard: { enabled: boolean } } = {boundingbox:[-9,7,9,-7],axis:true,showCopyright:false,showNavigation:false,keepaspectratio:true,pan:{enabled:false},zoom:{wheel:false},keyboard:{enabled:false},resize:{enabled:false,throttle:100}};
    const b=JXG.JSXGraph.initBoard(element,options);
    element.style.touchAction="pan-y";
    board.current=b;
    const initial=latest.current.p;
    const point=(key:string)=>{
      const obj=b.create("point",[Number(initial[key+"x"]),Number(initial[key+"y"])],{name:key.toUpperCase(),size:4,strokeColor:"#345c9c",fillColor:"#345c9c",label:{display:"internal"}});
      obj.on("up",()=>{latest.current.onChange(key+"x",Math.round(Math.min(8,Math.max(-8,obj.X()))*2)/2);latest.current.onChange(key+"y",Math.round(Math.min(6,Math.max(-6,obj.Y()))*2)/2);});
      points.current[key]=obj;return obj;
    };
    const a=point("a");
    const attrs={strokeColor:"#345c9c",strokeWidth:2};
    if(template==="circle_geometry") b.create("circle",[a,()=>Number(latest.current.p.radius)],attrs);
    else if(template!=="point_geometry"){
      const second=point("b");
      const segment=b.create("segment",[a,second],attrs);
      if(template==="triangle_angles"){
        const c=point("c");
        b.create("polygon",[a,second,c],{fillColor:"#e5edf8",fillOpacity:.65,borders:attrs,vertices:{visible:false}});
        for(const vertices of [[second,a,c],[a,second,c],[a,c,second]]) b.create("nonreflexangle",vertices,{radius:.6,fillColor:"#d3e6ff",name:"",withLabel:false});
      }else if(template==="parallel_lines" || template==="perpendicular_lines"){
        const line=b.create("line",[a,second],attrs);
        if(template==="parallel_lines"){
          const offset=b.create("point",[()=>a.X()+1,()=>a.Y()+3],{visible:false,fixed:true});
          b.create("parallel",[line,offset],{...attrs,strokeColor:"#a0461b"});
        }else b.create("perpendicular",[line,a],{...attrs,strokeColor:"#a0461b"});
      }else if(template==="perpendicular_bisector"){
        const midpoint=b.create("midpoint",[a,second],{name:"M",size:3,label:{display:"internal"}});
        b.create("perpendicular",[segment,midpoint],{...attrs,strokeColor:"#a0461b"});
      }
    }
    return ()=>{points.current={};board.current=null;JXG.JSXGraph.freeBoard(b);};
  },[template]);
  useEffect(()=>{
    const b=board.current;if(!b)return;
    b.suspendUpdate();
    for(const [key,point]of Object.entries(points.current))point.setPosition(JXG.COORDS_BY_USER,[Number(p[key+"x"]),Number(p[key+"y"])]);
    b.unsuspendUpdate();
  },[p]);
  useEffect(()=>{board.current?.resizeContainer(width,height);},[width,height]);
  // Numeric controls outside the board provide equivalent keyboard operation.
  return <div ref={host} className="math-geometry-board" role="img" aria-label="Geometry construction; use the coordinate controls to move points." style={{width,height}} />;
}
