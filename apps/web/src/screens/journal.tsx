import { useCallback, useEffect, useState } from "react"

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { SectionHeader } from "@/components/ui/section-header"
import { Textarea } from "@/components/ui/textarea"
import { api } from "@/lib/api"
import type { JournalEntry } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

export function JournalScreen({ locale }: { locale: Locale }) {
  const [entries, setEntries] = useState<JournalEntry[]>([])
  const [body, setBody] = useState("")
  const [title, setTitle] = useState("")
  const [mood, setMood] = useState<number | "">("")
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(() => {
    api
      .journal()
      .then((payload) => setEntries(payload.entries))
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(reload, [reload])

  const save = async () => {
    if (!body.trim()) return
    try {
      await api.createJournal({
        body: body.trim(),
        title: title.trim() || undefined,
        mood: mood === "" ? undefined : Number(mood),
        tags: [],
      })
      setBody("")
      setTitle("")
      setMood("")
      setNotice(t(locale, "journalSaved"))
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const remove = async (id: string) => {
    try {
      await api.deleteJournal(id)
      reload()
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  const exportAll = async () => {
    try {
      const result = await api.exportData()
      setNotice(`${t(locale, "journalExported")}: ${result.path}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    }
  }

  return (
    <>
      <SectionHeader
        as="h1"
        title={t(locale, "journalTitle")}
        description={t(locale, "journalLead")}
        action={
          <Button variant="outline" onClick={() => void exportAll()}>
            {t(locale, "journalExport")}
          </Button>
        }
      />

      {notice && (
        <Alert>
          <AlertDescription className="break-all">{notice}</AlertDescription>
        </Alert>
      )}
      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      <Card>
        <CardHeader>
          <CardTitle>{t(locale, "journalNew")}</CardTitle>
        </CardHeader>
        <CardContent>
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="journal-title">{t(locale, "journalTitleField")}</FieldLabel>
              <Input
                id="journal-title"
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="journal-body">{t(locale, "journalBody")}</FieldLabel>
              <Textarea
                id="journal-body"
                rows={5}
                value={body}
                onChange={(event) => setBody(event.target.value)}
              />
            </Field>
            <Field>
              <FieldLabel htmlFor="journal-mood">{t(locale, "journalMood")}</FieldLabel>
              <Input
                id="journal-mood"
                type="number"
                min={1}
                max={5}
                value={mood}
                onChange={(event) =>
                  setMood(event.target.value === "" ? "" : Number(event.target.value))
                }
                className="max-w-24"
              />
            </Field>
            <div>
              <Button onClick={() => void save()} disabled={!body.trim()}>
                {t(locale, "journalSave")}
              </Button>
            </div>
          </FieldGroup>
        </CardContent>
      </Card>

      {entries.length === 0 ? (
        <EmptyState title={t(locale, "journalEmpty")} />
      ) : (
        <div className="flex flex-col gap-3">
          {entries.map((entry) => (
            <Card key={entry.id}>
              <CardHeader>
                <CardTitle className="flex items-center justify-between gap-3 text-base">
                  <span>{entry.title ?? entry.created_at}</span>
                  <span className="flex items-center gap-2">
                    {entry.mood !== null && <Badge variant="secondary">{entry.mood}/5</Badge>}
                    <AlertDialog>
                      <AlertDialogTrigger render={<Button variant="ghost" size="sm" />}>
                        {t(locale, "journalDelete")}
                      </AlertDialogTrigger>
                      <AlertDialogContent>
                        <AlertDialogHeader>
                          <AlertDialogTitle>{t(locale, "journalDeleteConfirm")}</AlertDialogTitle>
                          <AlertDialogDescription>{entry.created_at}</AlertDialogDescription>
                        </AlertDialogHeader>
                        <AlertDialogFooter>
                          <AlertDialogCancel>{t(locale, "journalCancel")}</AlertDialogCancel>
                          <AlertDialogAction onClick={() => void remove(entry.id)}>
                            {t(locale, "journalDelete")}
                          </AlertDialogAction>
                        </AlertDialogFooter>
                      </AlertDialogContent>
                    </AlertDialog>
                  </span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="whitespace-pre-wrap text-sm text-muted-foreground">{entry.body}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
