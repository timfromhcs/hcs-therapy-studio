import { useCallback, useEffect, useState } from "react"
import { Database, Search } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { EmptyState } from "@/components/ui/empty-state"
import { Input } from "@/components/ui/input"
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
import type { AuditEvent, KnowledgeHit, KnowledgeStats, ModelInfo, StorageUsage } from "@/lib/api"
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
  const [knowledge, setKnowledge] = useState<KnowledgeStats | null>(null)
  const [query, setQuery] = useState("")
  const [hits, setHits] = useState<KnowledgeHit[] | null>(null)
  const [searching, setSearching] = useState(false)
  const [emptyReason, setEmptyReason] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    Promise.all([api.models(), api.audit(), api.storage(), api.knowledgeStats()])
      .then(([modelPayload, auditPayload, storagePayload, stats]) => {
        if (!alive) return
        setModels(modelPayload.models)
        setEvents(auditPayload.events)
        setStorage(storagePayload)
        setKnowledge(stats)
      })
      .catch((err: Error) => alive && setError(err.message))
    return () => {
      alive = false
    }
  }, [])

  const search = useCallback(async () => {
    const text = query.trim()
    if (!text) return
    setSearching(true)
    setError(null)
    try {
      const result = await api.knowledgeSearch(text, 6)
      setHits(result.hits)
      setEmptyReason(result.empty_reason)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSearching(false)
    }
  }, [query])

  const reindex = useCallback(async () => {
    setSearching(true)
    setError(null)
    try {
      const result = await api.knowledgeReindex()
      setKnowledge(result.stats)
      const audit = await api.audit()
      setEvents(audit.events)
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setSearching(false)
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
          <CardTitle className="flex items-center gap-2 text-base">
            <Database aria-hidden="true" className="size-4" />
            {t(locale, "labKnowledge")}
          </CardTitle>
        </CardHeader>
        <CardContent className="flex flex-col gap-4">
          {knowledge ? (
            <div className="flex flex-wrap gap-2 text-xs">
              <Badge variant="secondary">
                {knowledge.documents} {t(locale, "labKnowledgeDocs")}
              </Badge>
              <Badge variant="secondary">
                {knowledge.chunks} {t(locale, "labKnowledgeChunks")}
              </Badge>
              <Badge variant={knowledge.encrypted ? "secondary" : "destructive"}>
                {knowledge.encrypted ? t(locale, "settingsEncryption") : t(locale, "labUnapproved")}
              </Badge>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">{t(locale, "commonLoading")}</p>
          )}

          {knowledge && (
            <p className="text-xs text-muted-foreground">
              {knowledge.retriever}. {knowledge.note}
            </p>
          )}

          <div className="flex flex-wrap items-end gap-2">
            <Input
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter") void search()
              }}
              placeholder={t(locale, "labKnowledgePlaceholder")}
              aria-label={t(locale, "labKnowledgeSearch")}
              className="min-w-48 flex-1"
            />
            <Button onClick={() => void search()} disabled={searching || !query.trim()}>
              <Search />
              <span className="ml-1">{t(locale, "labKnowledgeSearch")}</span>
            </Button>
            <Button variant="outline" onClick={() => void reindex()} disabled={searching}>
              {t(locale, "labKnowledgeReindex")}
            </Button>
          </div>

          {hits !== null &&
            (hits.length === 0 ? (
              <p className="text-sm text-muted-foreground">
                {t(locale, "labKnowledgeNoHits")}
                {emptyReason ? ` (${emptyReason})` : ""}
              </p>
            ) : (
              <ol className="flex flex-col gap-3">
                {hits.map((hit) => (
                  <li key={hit.chunk_id} className="rounded-[var(--radius-card)] border p-3">
                    <div className="mb-1 flex flex-wrap items-center gap-2 text-xs text-muted-foreground">
                      <span className="font-mono">{hit.citation}</span>
                      <span>{hit.title ?? hit.source}</span>
                      <span className="tabular-nums">{t(locale, "labKnowledgeScore")} {hit.score.toFixed(3)}</span>
                      {hit.rank_word && (
                        <span className="tabular-nums">BM25 #{hit.rank_word}</span>
                      )}
                      {hit.rank_trigram && (
                        <span className="tabular-nums">3-gram #{hit.rank_trigram}</span>
                      )}
                    </div>
                    <p className="text-sm">{hit.text}</p>
                  </li>
                ))}
              </ol>
            ))}
        </CardContent>
      </Card>

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
