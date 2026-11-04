/**
 * Constrained scene renderer — the browser mirror of
 * `hcs_therapy/svg.py::render_scene`.
 *
 * The editor never accepts SVG markup from a user or a model. It accepts a
 * validated scene object and renders it itself, so the same limits apply in
 * both implementations: bounded integers, `#rrggbb` colours only, escaped text,
 * no attributes a renderer could execute.
 *
 * If the two implementations ever disagree, the Python one is authoritative for
 * exported files; this one is what the canvas shows.
 */

export type SceneElement =
  | {
      type: "rect"
      x: number
      y: number
      w: number
      h: number
      fill: string
      stroke?: string
    }
  | { type: "circle"; x: number; y: number; r: number; fill: string }
  | { type: "line"; x: number; y: number; x2: number; y2: number; stroke: string; strokeWidth: number }
  | {
      type: "text"
      x: number
      y: number
      text: string
      fontSize: number
      fill: string
      anchor?: "start" | "middle" | "end"
    }

export type Scene = {
  width: number
  height: number
  background: string
  elements: SceneElement[]
}

const COLOUR = /^#[0-9a-fA-F]{6}$/

export class SceneError extends Error {}

function clamp(value: number, low: number, high: number, name: string): number {
  if (!Number.isFinite(value)) throw new SceneError(`${name} must be a number`)
  const rounded = Math.round(value)
  if (rounded < low || rounded > high) {
    throw new SceneError(`${name} must be between ${low} and ${high}`)
  }
  return rounded
}

function colour(value: string, name: string): string {
  if (!COLOUR.test(value)) throw new SceneError(`${name} must be a #rrggbb colour`)
  return value
}

function escapeText(text: string): string {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
}

export function renderScene(scene: Scene): string {
  const width = clamp(scene.width, 100, 4000, "width")
  const height = clamp(scene.height, 100, 4000, "height")
  const background = colour(scene.background, "background")
  if (scene.elements.length > 200) throw new SceneError("at most 200 elements")

  const parts: string[] = [
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}" role="img">`,
    `<rect x="0" y="0" width="${width}" height="${height}" fill="${background}"/>`,
  ]

  scene.elements.forEach((element, index) => {
    switch (element.type) {
      case "rect": {
        const x = clamp(element.x, 0, width, `element ${index} x`)
        const y = clamp(element.y, 0, height, `element ${index} y`)
        const w = clamp(element.w, 1, width, `element ${index} w`)
        const h = clamp(element.h, 1, height, `element ${index} h`)
        const stroke = element.stroke ? ` stroke="${colour(element.stroke, "stroke")}"` : ""
        parts.push(
          `<rect x="${x}" y="${y}" width="${w}" height="${h}" fill="${colour(element.fill, "fill")}"${stroke}/>`,
        )
        break
      }
      case "circle": {
        const cx = clamp(element.x, 0, width, `element ${index} x`)
        const cy = clamp(element.y, 0, height, `element ${index} y`)
        const r = clamp(element.r, 1, Math.min(width, height), `element ${index} r`)
        parts.push(`<circle cx="${cx}" cy="${cy}" r="${r}" fill="${colour(element.fill, "fill")}"/>`)
        break
      }
      case "line": {
        parts.push(
          `<line x1="${clamp(element.x, 0, width, "x1")}" y1="${clamp(element.y, 0, height, "y1")}" x2="${clamp(
            element.x2,
            0,
            width,
            "x2",
          )}" y2="${clamp(element.y2, 0, height, "y2")}" stroke="${colour(element.stroke, "stroke")}" stroke-width="${clamp(
            element.strokeWidth,
            1,
            40,
            "strokeWidth",
          )}"/>`,
        )
        break
      }
      case "text": {
        if (element.text.length > 500) throw new SceneError("text is limited to 500 characters")
        const anchor = element.anchor ?? "start"
        if (!["start", "middle", "end"].includes(anchor)) throw new SceneError("bad anchor")
        parts.push(
          `<text x="${clamp(element.x, 0, width, "x")}" y="${clamp(element.y, 0, height, "y")}" font-size="${clamp(
            element.fontSize,
            6,
            400,
            "fontSize",
          )}" font-family="system-ui" fill="${colour(element.fill, "fill")}" text-anchor="${anchor}">${escapeText(
            element.text,
          )}</text>`,
        )
        break
      }
      default:
        throw new SceneError(`unsupported element type`)
    }
  })

  parts.push("</svg>")
  return parts.join("")
}

export function emptyScene(): Scene {
  return {
    width: 1080,
    height: 1080,
    background: "#f7f4ec",
    elements: [],
  }
}

export function presetCard(): Scene {
  return {
    width: 1080,
    height: 1350,
    background: "#f7f4ec",
    elements: [
      { type: "rect", x: 96, y: 96, w: 888, h: 1158, fill: "#ffffff", stroke: "#e4ded2" },
      { type: "text", x: 144, y: 240, text: "Heute", fontSize: 72, fill: "#1f1d1a" },
      {
        type: "text",
        x: 144,
        y: 330,
        text: "Ein Satz, den ich behalten will.",
        fontSize: 34,
        fill: "#5c574e",
      },
      { type: "line", x: 144, y: 392, x2: 936, y2: 392, stroke: "#e4ded2", strokeWidth: 2 },
    ],
  }
}

export function presetWorksheet(): Scene {
  return {
    width: 1240,
    height: 1754,
    background: "#ffffff",
    elements: [
      { type: "text", x: 96, y: 140, text: "Gedankenprotokoll", fontSize: 64, fill: "#1f1d1a" },
      {
        type: "text",
        x: 96,
        y: 200,
        text: "Situation · Gedanke · Gefühl · fairerer Gedanke",
        fontSize: 28,
        fill: "#5c574e",
      },
      { type: "rect", x: 96, y: 260, w: 1048, h: 300, fill: "#faf8f3", stroke: "#e4ded2" },
      { type: "rect", x: 96, y: 600, w: 1048, h: 300, fill: "#faf8f3", stroke: "#e4ded2" },
      { type: "rect", x: 96, y: 940, w: 1048, h: 300, fill: "#faf8f3", stroke: "#e4ded2" },
      { type: "rect", x: 96, y: 1280, w: 1048, h: 360, fill: "#faf8f3", stroke: "#e4ded2" },
    ],
  }
}
