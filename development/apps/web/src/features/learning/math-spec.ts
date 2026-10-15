import registry from "./math-templates.json";

export type MathParameters = Record<string, number | string>;
export type MathTemplate = keyof typeof registry;
export type MathVisualBlock = { id: string; kind: "math_visual"; version: 1; template: MathTemplate; title: string; description: string; parameters: MathParameters };
export type ParameterSpec = { label: string; default: number | string; min?: number; max?: number; step?: number; options?: string[] };
export type TemplateSpec = { engine: "konva" | "jsxgraph" | "mafs"; label: string; minLevel: number; parameters: Record<string, ParameterSpec> };
export const mathTemplates = registry as Record<MathTemplate, TemplateSpec>;
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === "object" && !Array.isArray(value);
const label = (value: unknown, max: number): value is string => typeof value === "string" && !!value.trim() && value.length <= max && !/[\u0000-\u0008\u000b-\u001f]/.test(value);
export function isMathVisualBlock(value: unknown): value is MathVisualBlock {
  if (!record(value) || value.kind !== "math_visual" || value.version !== 1 || !label(value.id, 100) || !label(value.title, 200) || !label(value.description, 500) ||
      typeof value.template !== "string" || !Object.hasOwn(mathTemplates, value.template) || !record(value.parameters) ||
      Object.keys(value).some(key => !["id", "kind", "version", "template", "title", "description", "parameters"].includes(key))) return false;
  const spec = mathTemplates[value.template as MathTemplate], p = value.parameters;
  if (Object.keys(p).length !== Object.keys(spec.parameters).length) return false;
  for (const [key, field] of Object.entries(spec.parameters)) {
    const v = p[key];
    if (field.options ? typeof v !== "string" || !field.options.includes(v) :
      typeof v !== "number" || !Number.isFinite(v) || v < field.min! || v > field.max! ||
      (field.step === 1 && !Number.isInteger(v)) || Math.abs(v - Math.round(v * 1000) / 1000) > 1e-8) return false;
  }
  if (value.template.startsWith("fraction_") && Number(p.numerator) > Number(p.denominator)) return false;
  if (value.template === "number_line" && !(Number(p.start) < Number(p.end) && Number(p.value) >= Number(p.start) && Number(p.value) <= Number(p.end))) return false;
  if ("bx" in p && Math.hypot(Number(p.ax) - Number(p.bx), Number(p.ay) - Number(p.by)) < .1) return false;
  return value.template !== "triangle_angles" || triangleArea(p as MathParameters) >= .05;
}
export function triangleArea(p: MathParameters) {
  return Math.abs((Number(p.bx)-Number(p.ax))*(Number(p.cy)-Number(p.ay))-(Number(p.by)-Number(p.ay))*(Number(p.cx)-Number(p.ax))) / 2;
}
export function functionValue(template: MathTemplate, p: MathParameters, x: number) {
  if (template === "trigonometric_function") {
    const angle = Number(p.k) * (x - Number(p.h));
    return Number(p.a) * (p.function === "cos" ? Math.cos(angle) : Math.sin(angle)) + Number(p.d);
  }
  return template === "linear_function" ? Number(p.m) * x + Number(p.b) : Number(p.a) * x * x + Number(p.b) * x + Number(p.c);
}
export function changeMathParameter(template: MathTemplate, current: MathParameters, key: string, value: number | string): MathParameters {
  const spec = mathTemplates[template].parameters[key];
  if (!spec) return current;
  if (spec.options && (typeof value !== "string" || !spec.options.includes(value))) return current;
  if (!spec.options && (typeof value !== "number" || !Number.isFinite(value))) return current;
  const number = Math.max(spec.min ?? 0, Math.min(spec.max ?? 0, Number(value)));
  const p = { ...current, [key]: spec.options ? value : spec.step === 1 ? Math.round(number) : Math.round(number * 1000) / 1000 };
  if (template.startsWith("fraction_")) p.numerator = Math.min(Number(p.numerator), Number(p.denominator));
  if (template === "number_line") {
    if (Number(p.start) >= Number(p.end)) p[key] = current[key];
    p.value = Math.min(Number(p.end), Math.max(Number(p.start), Number(p.value)));
  }
  return p;
}
const tidy = (n: number) => Number.isFinite(n) ? String(Math.round(n * 100) / 100) : "undefined";
export function mathState(template: MathTemplate, p: MathParameters): string {
  if (template === "counting_groups") return `${p.count} objects: ${Math.floor(Number(p.count) / Number(p.groupSize))} full groups of ${p.groupSize}, ${Number(p.count) % Number(p.groupSize)} remaining.`;
  if (template.startsWith("fraction_")) return `${p.numerator} of ${p.denominator} equal parts shaded (${p.numerator}/${p.denominator}).`;
  if (template === "number_line") return `Position ${p.value} on the number line from ${p.start} to ${p.end}.`;
  if (template === "ruler_measurement") return `Length: ${p.length} mathematical units. The screen is not a physically calibrated ruler.`;
  if (template === "shape_explorer") return `${p.shape}; width/radius ${p.width} units${p.shape === "circle" ? "" : `, height ${p.height} units`}.`;
  if (template === "coordinate_points") return `Point (${p.x}, ${p.y}).`;
  if (template.endsWith("function")) return `${template === "linear_function" ? `y = ${p.m}x + ${p.b}` : template === "trigonometric_function" ? `y = ${p.a} ${p.function}(${p.k}(x − ${p.h})) + ${p.d} (radians)` : `y = ${p.a}x² + ${p.b}x + ${p.c}`}; at x = ${p.x}, y = ${tidy(functionValue(template, p, Number(p.x)))}.`;
  if (template === "triangle_angles") {
    if (triangleArea(p) < .05) return "The points are collinear: move a vertex to form a triangle.";
    const angle = (x: string, a: string, b: string) => {
      const ux=Number(p[a+"x"])-Number(p[x+"x"]), uy=Number(p[a+"y"])-Number(p[x+"y"]);
      const vx=Number(p[b+"x"])-Number(p[x+"x"]), vy=Number(p[b+"y"])-Number(p[x+"y"]);
      return Math.acos(Math.max(-1,Math.min(1,(ux*vx+uy*vy)/(Math.hypot(ux,uy)*Math.hypot(vx,vy))))) * 180 / Math.PI;
    };
    return `Angles: A ${tidy(angle("a","b","c"))}°, B ${tidy(angle("b","a","c"))}°, C ${tidy(angle("c","a","b"))}°. Sum 180°. Area ${tidy(triangleArea(p))} square units.`;
  }
  if (template === "circle_geometry") return `Centre (${p.ax}, ${p.ay}), radius ${p.radius} units; circumference ${tidy(2*Math.PI*Number(p.radius))} units.`;
  if (template === "point_geometry") return `A (${p.ax}, ${p.ay}).`;
  const distance = Math.hypot(Number(p.bx)-Number(p.ax),Number(p.by)-Number(p.ay));
  if (distance < .1) return "The endpoints coincide: move a point to restore the construction.";
  return `A (${p.ax}, ${p.ay}), B (${p.bx}, ${p.by}); segment length ${tidy(distance)} units.${template === "perpendicular_bisector" ? ` Midpoint (${tidy((Number(p.ax)+Number(p.bx))/2)}, ${tidy((Number(p.ay)+Number(p.by))/2)}); bisector meets AB at 90°.` : template === "perpendicular_lines" ? " Lines meet at 90°." : template === "parallel_lines" ? " Both lines have the same direction." : ""}`;
}
