import { useState } from "react"

import { Alert, AlertDescription } from "@/components/ui/alert"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { SectionHeader } from "@/components/ui/section-header"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

const FIELDS = [
  { key: "situation", labelKey: "reflectionSituation" },
  { key: "thought", labelKey: "reflectionThought" },
  { key: "feeling", labelKey: "reflectionFeeling" },
  { key: "for", labelKey: "reflectionEvidenceFor" },
  { key: "against", labelKey: "reflectionEvidenceAgainst" },
  { key: "alternative", labelKey: "reflectionAlternative" },
] as const

type FieldKey = (typeof FIELDS)[number]["key"]

export function ReflectionScreen({ locale }: { locale: Locale }) {
  const [values, setValues] = useState<Record<FieldKey, string>>({
    situation: "",
    thought: "",
    feeling: "",
    for: "",
    against: "",
    alternative: "",
  })
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const set = (key: FieldKey, value: string) =>
    setValues((current) => ({ ...current, [key]: value }))

  const canSave = values.situation.trim().length > 0 && values.thought.trim().length > 0

  const save = async () => {
    if (!canSave) return
    const body = [
      `${t(locale, "reflectionSituation")}: ${values.situation.trim()}`,
      `${t(locale, "reflectionThought")}: ${values.thought.trim()}`,
      values.feeling.trim() && `${t(locale, "reflectionFeeling")}: ${values.feeling.trim()}`,
      values.for.trim() && `${t(locale, "reflectionEvidenceFor")}: ${values.for.trim()}`,
      values.against.trim() && `${t(locale, "reflectionEvidenceAgainst")}: ${values.against.trim()}`,
      values.alternative.trim() && `${t(locale, "reflectionAlternative")}: ${values.alternative.trim()}`,
    ]
      .filter(Boolean)
      .join("\n\n")

    try {
      await api.createJournal({
        body,
        title: `${t(locale, "reflectionTitle")} — ${values.situation.trim().slice(0, 40)}`,
        tags: ["reflexion"],
      })
      setNotice(t(locale, "journalSaved"))
      setValues({ situation: "", thought: "", feeling: "", for: "", against: "", alternative: "" })
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <>
      <SectionHeader
        as="h1"
        title={t(locale, "reflectionTitle")}
        description={t(locale, "reflectionLead")}
      />

      {notice && (
        <Alert>
          <AlertDescription>{notice}</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardContent className="pt-6">
          <FieldGroup>
            {FIELDS.map((field) => (
              <Field key={field.key}>
                <FieldLabel htmlFor={`reflection-${field.key}`}>
                  {t(locale, field.labelKey)}
                </FieldLabel>
                <Textarea
                  id={`reflection-${field.key}`}
                  rows={2}
                  value={values[field.key]}
                  onChange={(event) => set(field.key, event.target.value)}
                />
              </Field>
            ))}
            <Field>
              <FieldDescription>{t(locale, "reflectionHint")}</FieldDescription>
              <Button onClick={() => void save()} disabled={!canSave}>
                {t(locale, "reflectionSave")}
              </Button>
            </Field>
          </FieldGroup>
        </CardContent>
      </Card>
    </>
  )
}
