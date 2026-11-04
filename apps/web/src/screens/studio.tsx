import { useMemo, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { SectionHeader } from "@/components/ui/section-header"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"
import type { Scene, SceneElement } from "@/lib/scene"
import { emptyScene, presetCard, presetWorksheet, renderScene } from "@/lib/scene"

type Kind = "rect" | "text" | "circle"

function newElement(kind: Kind, scene: Scene): SceneElement {
  const base = Math.round(Math.min(scene.width, scene.height) * 0.1)
  if (kind === "text") {
    return {
      type: "text",
      x: base,
      y: base * 2,
      text: "Text",
      fontSize: 48,
      fill: "#1f1d1a",
      anchor: "start",
    }
  }
  if (kind === "circle") {
    return { type: "circle", x: base * 3, y: base * 3, r: base, fill: "#8aa3c8" }
  }
  return { type: "rect", x: base, y: base, w: base * 3, h: base * 2, fill: "#e4ded2" }
}

export function StudioScreen({ locale }: { locale: Locale }) {
  const [scene, setScene] = useState<Scene>(emptyScene)
  const [selected, setSelected] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)

  const svg = useMemo(() => {
    try {
      setError(null)
      return renderScene(scene)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
      return ""
    }
  }, [scene])

  const update = (patch: Partial<SceneElement>) => {
    if (selected === null) return
    setScene((current) => ({
      ...current,
      elements: current.elements.map((element, index) =>
        index === selected ? ({ ...element, ...patch } as SceneElement) : element,
      ),
    }))
  }

  const add = (kind: Kind) => {
    setScene((current) => {
      const element = newElement(kind, current)
      setSelected(current.elements.length)
      return { ...current, elements: [...current.elements, element] }
    })
  }

  const removeSelected = () => {
    if (selected === null) return
    setScene((current) => ({
      ...current,
      elements: current.elements.filter((_, index) => index !== selected),
    }))
    setSelected(null)
  }

  const download = () => {
    if (!svg) return
    const blob = new Blob([svg], { type: "image/svg+xml" })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement("a")
    anchor.href = url
    anchor.download = "hcs-layout.svg"
    anchor.click()
    URL.revokeObjectURL(url)
  }

  const element = selected === null ? null : scene.elements[selected]

  return (
    <>
      <SectionHeader
        as="h1"
        title={t(locale, "studioTitle")}
        description={t(locale, "studioLead")}
        action={
          <Button onClick={download} disabled={!svg}>
            {t(locale, "studioExport")}
          </Button>
        }
      />

      <div className="grid gap-4 lg:grid-cols-[1fr_20rem]">
        <Card className="overflow-hidden">
          <CardContent className="flex items-center justify-center bg-muted/40 p-4">
            {svg ? (
              <div
                className="w-full max-w-xl [&>svg]:h-auto [&>svg]:w-full"
                // The SVG is produced by our own validated renderer, never by a
                // model or a user-supplied document.
                dangerouslySetInnerHTML={{ __html: svg }}
              />
            ) : (
              <p className="py-16 text-sm text-muted-foreground">{error}</p>
            )}
          </CardContent>
        </Card>

        <div className="flex flex-col gap-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t(locale, "studioPreset")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => setScene(presetCard())}>
                {t(locale, "studioPresetCard")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setScene(presetWorksheet())}>
                {t(locale, "studioPresetWorksheet")}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">{t(locale, "studioAddRect")}</CardTitle>
            </CardHeader>
            <CardContent className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={() => add("rect")}>
                {t(locale, "studioAddRect")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => add("text")}>
                {t(locale, "studioAddText")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => add("circle")}>
                {t(locale, "studioAddCircle")}
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">
                {element ? `${element.type} #${selected! + 1}` : t(locale, "studioEmpty")}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <FieldGroup>
                <div className="flex gap-2">
                  <Field>
                    <FieldLabel>{t(locale, "studioWidth")}</FieldLabel>
                    <Input
                      type="number"
                      value={scene.width}
                      onChange={(event) =>
                        setScene((current) => ({ ...current, width: Number(event.target.value) }))
                      }
                    />
                  </Field>
                  <Field>
                    <FieldLabel>{t(locale, "studioHeight")}</FieldLabel>
                    <Input
                      type="number"
                      value={scene.height}
                      onChange={(event) =>
                        setScene((current) => ({ ...current, height: Number(event.target.value) }))
                      }
                    />
                  </Field>
                </div>

                {scene.elements.length > 0 && (
                  <Field>
                    <FieldLabel>{t(locale, "studioEmpty")}</FieldLabel>
                    <Select
                      value={selected === null ? "" : String(selected)}
                      onValueChange={(value) => setSelected(Number(value))}
                    >
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {scene.elements.map((item, index) => (
                          <SelectItem key={index} value={String(index)}>
                            {`${index + 1}. ${item.type}`}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </Field>
                )}

                {element && (
                  <>
                    <div className="flex gap-2">
                      <Field>
                        <FieldLabel>X</FieldLabel>
                        <Input
                          type="number"
                          value={element.x}
                          onChange={(event) => update({ x: Number(event.target.value) })}
                        />
                      </Field>
                      <Field>
                        <FieldLabel>Y</FieldLabel>
                        <Input
                          type="number"
                          value={element.y}
                          onChange={(event) => update({ y: Number(event.target.value) })}
                        />
                      </Field>
                    </div>

                    {element.type === "text" && (
                      <Field>
                        <FieldLabel>{t(locale, "studioElementText")}</FieldLabel>
                        <Input
                          value={element.text}
                          onChange={(event) => update({ text: event.target.value })}
                        />
                      </Field>
                    )}

                    <Field>
                      <FieldLabel>{t(locale, "studioFill")}</FieldLabel>
                      <Input
                        type="color"
                        className="h-9 w-16 p-1"
                        value={"fill" in element ? element.fill : "#000000"}
                        onChange={(event) =>
                          update({ fill: event.target.value } as Partial<SceneElement>)
                        }
                      />
                    </Field>

                    <Button variant="outline" size="sm" onClick={removeSelected}>
                      {t(locale, "studioRemove")}
                    </Button>
                  </>
                )}
              </FieldGroup>
            </CardContent>
          </Card>
        </div>
      </div>
    </>
  )
}
