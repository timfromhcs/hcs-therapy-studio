import { useEffect, useRef, useState } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { SectionHeader } from "@/components/ui/section-header"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"
import { api, ApiError } from "@/lib/api"
import type { ChatMeta, Resources } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

type Message = {
  role: "user" | "assistant"
  content: string
  meta?: ChatMeta
}

export function ChatScreen({
  locale,
  health,
}: {
  locale: Locale
  health: { modelLoaded: boolean }
}) {
  const [messages, setMessages] = useState<Message[]>([])
  const [draft, setDraft] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [crisis, setCrisis] = useState<Resources | null>(null)
  const endRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, busy])

  const loadResources = async () => {
    try {
      setCrisis(await api.resources())
    } catch {
      setCrisis(null)
    }
  }

  const send = async () => {
    const text = draft.trim()
    if (!text || busy) return
    setError(null)
    setDraft("")
    const next: Message[] = [...messages, { role: "user", content: text }]
    setMessages(next)
    setBusy(true)
    try {
      const result = await api.chat(next.map(({ role, content }) => ({ role, content })))
      setMessages([...next, { role: "assistant", content: result.content, meta: result.meta }])
      if (result.meta?.resources_shown) void loadResources()
    } catch (err) {
      const message = err instanceof ApiError ? err.message : String(err)
      setError(message)
    } finally {
      setBusy(false)
    }
  }

  const policyView = messages
    .map((message) => message.meta)
    .filter((meta): meta is ChatMeta => Boolean(meta))
    .at(-1)

  return (
    <>
      <SectionHeader as="h1" title={t(locale, "chatTitle")} description={t(locale, "chatLead")} />

      <div className="-mt-3 flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="max-w-full whitespace-normal text-left">
          {t(locale, "scope")}
        </Badge>
      </div>

      {policyView?.resources_shown && crisis && (
        <div role="region" aria-label={t(locale, "crisisTitle")}>
          <Card className="border-pop-red-border bg-pop-red-surface">
            <CardContent className="flex flex-col gap-2 pt-6">
              <h2 className="text-base font-semibold text-pop-red-ink">
                {t(locale, "crisisTitle")}
              </h2>
              {(() => {
                const region = (localStorage.getItem("hcs.region") ?? "DE").toUpperCase()
                const pack = crisis.packs[region] ?? crisis.packs.EU
                if (!pack) return null
                return (
                  <p className="text-sm text-pop-red-ink">
                    <span className="font-medium">{pack.label}:</span>{" "}
                    {pack.emergency.contact}
                    {pack.lines.map((line) => ` · ${line.name}: ${line.contact}`).join("")}
                  </p>
                )
              })()}
              <p className="text-xs text-pop-red-ink/80">{t(locale, "crisisNote")}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="min-h-[50svh]">
        <CardContent className="flex flex-col gap-4 pt-6">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">{t(locale, "chatEmpty")}</p>
          )}
          <div className="flex flex-col gap-4" aria-live="polite">
            {messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={
                  message.role === "user"
                    ? "max-w-[85%] self-end rounded-[var(--radius-card)] bg-primary px-4 py-3 text-sm text-primary-foreground"
                    : "max-w-[85%] self-start rounded-[var(--radius-card)] bg-muted px-4 py-3 text-sm"
                }
              >
                <p className="whitespace-pre-wrap break-words">{message.content}</p>
                {message.meta && (
                  <div className="mt-2 flex flex-wrap gap-2">
                    {message.meta.model_bypassed && (
                      <Badge variant="secondary">{t(locale, "chatBypassed")}</Badge>
                    )}
                    {message.meta.output_guard_ok === false && (
                      <Badge variant="destructive">{t(locale, "chatGuardTripped")}</Badge>
                    )}
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 text-sm text-muted-foreground">
                <Spinner /> {t(locale, "chatSending")}
              </div>
            )}
          </div>
          <div ref={endRef} />
        </CardContent>
      </Card>

      {error && (
        <Alert variant="destructive">
          <AlertTitle>{t(locale, "chatError")}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!health.modelLoaded && !error && (
        <Alert>
          <AlertDescription>{t(locale, "chatBackendDown")}</AlertDescription>
        </Alert>
      )}

      <div className="flex items-end gap-2">
        <Textarea
          value={draft}
          onChange={(event) => setDraft(event.target.value)}
          placeholder={t(locale, "chatPlaceholder")}
          rows={3}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault()
              void send()
            }
          }}
          aria-label={t(locale, "chatPlaceholder")}
        />
        <Button onClick={() => void send()} disabled={busy || !draft.trim()}>
          {t(locale, "chatSend")}
        </Button>
      </div>
    </>
  )
}
