import { useCallback, useEffect, useState } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SectionHeader } from "@/components/ui/section-header"
import { api } from "@/lib/api"
import type { Resources } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

export function SafetyScreen({ locale }: { locale: Locale }) {
  const [data, setData] = useState<Resources | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(() => {
    api
      .resources()
      .then(setData)
      .catch((err: Error) => setError(err.message))
  }, [])

  useEffect(load, [load])

  return (
    <>
      <SectionHeader
        as="h1"
        title={t(locale, "safetyTitle")}
        description={t(locale, "safetyLead")}
      />

      <Alert variant="destructive">
        <AlertTitle>{t(locale, "crisisTitle")}</AlertTitle>
        <AlertDescription>{t(locale, "safetyDisclaimer")}</AlertDescription>
      </Alert>

      {error && (
        <Alert>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {data &&
        Object.entries(data.packs).map(([region, pack]) => (
          <Card key={region}>
            <CardHeader>
              <CardTitle className="flex flex-wrap items-center gap-2 text-base">
                {pack.label}
                <Badge variant="secondary">{region}</Badge>
                <span className="text-xs font-normal text-muted-foreground">
                  {t(locale, "safetyReviewed")} {pack.reviewed_at}
                </span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex flex-col gap-2 text-sm">
              <p>
                <span className="font-medium">{pack.emergency.name}:</span>{" "}
                <span className="font-mono">{pack.emergency.contact}</span>
              </p>
              {pack.lines.map((line) => (
                <p key={line.name} className="text-muted-foreground">
                  <span className="font-medium text-foreground">{line.name}:</span>{" "}
                  <span className="font-mono text-foreground">{line.contact}</span> · {line.hours}{" "}
                  ·{" "}
                  <a
                    className="underline underline-offset-2"
                    href={line.source_url}
                    target="_blank"
                    rel="noreferrer noopener"
                  >
                    {t(locale, "safetySource")}
                  </a>
                </p>
              ))}
            </CardContent>
          </Card>
        ))}

      {data && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t(locale, "safetyUnknown")}</CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <p>{data.unknown.emergency}</p>
            {data.unknown.note && <p className="mt-2">{data.unknown.note}</p>}
            <p className="mt-2">
              {t(locale, "safetyReviewed")} {data.reviewed_at} · {t(locale, "safetyAlways")}: 112
            </p>
          </CardContent>
        </Card>
      )}
    </>
  )
}
