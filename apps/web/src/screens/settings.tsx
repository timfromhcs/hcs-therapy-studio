import { useEffect, useState } from "react"

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
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Field, FieldDescription, FieldGroup, FieldLabel } from "@/components/ui/field"
import { Input } from "@/components/ui/input"
import { SectionHeader } from "@/components/ui/section-header"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { api, getBaseUrl, getToken, setBaseUrl, setToken } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { storeLocale, t } from "@/lib/i18n"

const REGIONS = ["DE", "UK", "US", "EU"] as const

export function SettingsScreen({ locale }: { locale: Locale }) {
  const [baseUrl, setUrl] = useState(getBaseUrl())
  const [token, setTok] = useState(getToken())
  const [region, setRegion] = useState(localStorage.getItem("hcs.region") ?? "DE")
  const [language, setLanguage] = useState<Locale>(locale)
  const [notice, setNotice] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [version, setVersion] = useState<string | null>(null)

  useEffect(() => {
    api
      .version()
      .then((payload) => setVersion(payload.version))
      .catch(() => setVersion(null))
  }, [token])

  const save = () => {
    setBaseUrl(baseUrl)
    setToken(token)
    localStorage.setItem("hcs.region", region)
    storeLocale(language)
    setNotice(t(language, "settingsSaved"))
    window.location.reload()
  }

  const exportData = async () => {
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
        title={t(locale, "settingsTitle")}
        description={t(locale, "settingsLead")}
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
        <CardContent className="pt-6">
          <FieldGroup>
            <Field>
              <FieldLabel htmlFor="settings-base">{t(locale, "settingsBaseUrl")}</FieldLabel>
              <Input
                id="settings-base"
                value={baseUrl}
                onChange={(event) => setUrl(event.target.value)}
              />
              <FieldDescription>{`${t(locale, "settingsVersion")}: ${version ?? "—"}`}</FieldDescription>
            </Field>
            <Field>
              <FieldLabel htmlFor="settings-token">{t(locale, "settingsToken")}</FieldLabel>
              <Input
                id="settings-token"
                type="password"
                value={token}
                onChange={(event) => setTok(event.target.value)}
              />
              <FieldDescription>{t(locale, "settingsTokenHint")}</FieldDescription>
            </Field>
            <Field>
              <FieldLabel>{t(locale, "settingsLanguage")}</FieldLabel>
              <Select
                value={language}
                onValueChange={(value) => setLanguage(value as Locale)}
              >
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="de">Deutsch</SelectItem>
                  <SelectItem value="en">English</SelectItem>
                </SelectContent>
              </Select>
            </Field>
            <Field>
              <FieldLabel>{t(locale, "settingsRegion")}</FieldLabel>
              <Select value={region} onValueChange={(value) => setRegion(value ?? "DE")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {REGIONS.map((item) => (
                    <SelectItem key={item} value={item}>
                      {item}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </Field>
            <div>
              <Button onClick={save}>{t(locale, "settingsSave")}</Button>
            </div>
          </FieldGroup>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="flex flex-wrap items-center gap-2 pt-6">
          <Button variant="outline" onClick={() => void exportData()}>
            {t(locale, "settingsExport")}
          </Button>
          <AlertDialog>
            <AlertDialogTrigger render={<Button variant="destructive" />}>
              {t(locale, "settingsWipe")}
            </AlertDialogTrigger>
            <AlertDialogContent>
              <AlertDialogHeader>
                <AlertDialogTitle>{t(locale, "settingsWipeConfirm")}</AlertDialogTitle>
                <AlertDialogDescription>{t(locale, "journalLead")}</AlertDialogDescription>
              </AlertDialogHeader>
              <AlertDialogFooter>
                <AlertDialogCancel>{t(locale, "journalCancel")}</AlertDialogCancel>
                <AlertDialogAction
                  onClick={() => {
                    void api
                      .wipeData()
                      .then((result) => {
                        setNotice(
                          `${t(locale, "settingsWipe")}: ${Object.entries(result.deleted)
                            .map(([table, count]) => `${table} ${count}`)
                            .join(", ")}`,
                        )
                        setError(null)
                      })
                      .catch((err: Error) => setError(err.message))
                  }}
                >
                  {t(locale, "settingsWipe")}
                </AlertDialogAction>
              </AlertDialogFooter>
            </AlertDialogContent>
          </AlertDialog>
        </CardContent>
      </Card>
    </>
  )
}
