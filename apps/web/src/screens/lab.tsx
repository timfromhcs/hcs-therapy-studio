import { useEffect, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { SectionHeader } from "@/components/ui/section-header"
import { Spinner } from "@/components/ui/spinner"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { api } from "@/lib/api"
import type { AuditEvent, ModelInfo, StorageUsage } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

function gib(bytes: number): string {
  return `${(bytes / 1024 ** 3).toFixed(2)} GiB`
}

export function LabScreen({ locale }: { locale: Locale }) {
  const [models, setModels] = useState<ModelInfo[] | null>(null)
  const [events, setEvents] = useState<AuditEvent[]>([])
  const [storage, setStorage] = useState<StorageUsage | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    Promise.all([api.models(), api.audit(), api.storage()])
      .then(([modelPayload, auditPayload, storagePayload]) => {
        if (!alive) return
        setModels(modelPayload.models)
        setEvents(auditPayload.events)
        setStorage(storagePayload)
      })
      .catch((err: Error) => alive && setError(err.message))
    return () => {
      alive = false
    }
  }, [])

  return (
    <>
      <SectionHeader as="h1" title={t(locale, "labTitle")} description={t(locale, "labLead")} />

      {error && <p className="text-sm text-pop-red-ink">{error}</p>}
      {!models && !error && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> {t(locale, "commonLoading")}
        </div>
      )}

      {models && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t(locale, "labModels")}</CardTitle>
          </CardHeader>
          <CardContent>
            {models.length === 0 ? (
              <EmptyState title={t(locale, "labNone")} />
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>ID</TableHead>
                    <TableHead>{t(locale, "labApproved")}</TableHead>
                    <TableHead>{t(locale, "labStorage")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {models.map((model) => (
                    <TableRow key={model.id}>
                      <TableCell className="font-medium">
                        <span className="flex flex-col gap-1">
                          <span>{model.name}</span>
                          <span className="font-mono text-xs text-muted-foreground">
                            {model.id}
                          </span>
                        </span>
                      </TableCell>
                      <TableCell>
                        <span className="flex flex-wrap gap-1">
                          <Badge variant={model.approved ? "secondary" : "destructive"}>
                            {model.approved ? model.license_spdx : t(locale, "labUnapproved")}
                          </Badge>
                          <Badge variant={model.installed ? "default" : "outline"}>
                            {model.installed ? t(locale, "labInstalled") : t(locale, "labNotInstalled")}
                          </Badge>
                        </span>
                      </TableCell>
                      <TableCell className="tabular-nums">{gib(model.size_bytes)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
            {storage && (
              <p className="mt-4 text-xs text-muted-foreground">
                {t(locale, "labStorage")}: {gib(storage.models_bytes)} · {storage.models_count} ·{" "}
                <span className="font-mono">{storage.root}</span>
              </p>
            )}
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t(locale, "labAudit")}</CardTitle>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <EmptyState title={t(locale, "labNoAudit")} />
          ) : (
            <ul className="flex flex-col gap-2 text-sm">
              {events.slice(0, 20).map((event, index) => (
                <li key={`${event.created_at}-${index}`} className="flex flex-wrap gap-x-3 gap-y-1">
                  <span className="font-mono text-xs text-muted-foreground">
                    {event.created_at}
                  </span>
                  <span className="font-medium">{event.event}</span>
                  <span className="text-muted-foreground">{event.status}</span>
                  {event.tool && <span className="font-mono text-xs">{event.tool}</span>}
                  <span className="text-muted-foreground">{event.summary}</span>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </>
  )
}
