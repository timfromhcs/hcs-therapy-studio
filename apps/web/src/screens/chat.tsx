import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Check, Copy, RefreshCw, Square } from "lucide-react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { RichText } from "@/components/rich-text"
import { SectionHeader } from "@/components/ui/section-header"
import { Spinner } from "@/components/ui/spinner"
import { Switch } from "@/components/ui/switch"
import { Textarea } from "@/components/ui/textarea"
import { api, ApiError } from "@/lib/api"
import type { KnowledgeHit, Resources, StreamMeta } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

type Message = {
  role: "user" | "assistant"
  content: string
  meta?: StreamMeta
  sources?: KnowledgeHit[]
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
  const [thinking, setThinking] = useState<number | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [crisis, setCrisis] = useState<Resources | null>(null)
  const [useKnowledge, setUseKnowledge] = useState(false)
  const [copied, setCopied] = useState<number | null>(null)
  // Turns remaining in which the conversation must stay attentive after a crisis
  // hand-off. Client-side on purpose: the server stores no conversation.
  const [attentiveTurns, setAttentiveTurns] = useState(0)
  const endRef = useRef<HTMLDivElement>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" })
  }, [messages, busy, thinking])

  const loadResources = useCallback(async () => {
    try {
      setCrisis(await api.resources())
    } catch {
      setCrisis(null)
    }
  }, [])

  const runTurn = useCallback(
    async (history: Message[]) => {
      setError(null)
      setBusy(true)
      setThinking(null)
      const controller = new AbortController()
      abortRef.current = controller

      let answer = ""
      let index = -1
      setMessages([...history, { role: "assistant", content: "" }])
      index = history.length

      const update = (patch: Partial<Message>) => {
        setMessages((current) =>
          current.map((message, position) =>
            position === index ? { ...message, ...patch } : message,
          ),
        )
      }

      try {
        await api.chatStream(
          history.map(({ role, content }) => ({ role, content })),
          {
            signal: controller.signal,
            useKnowledge,
            attentive: attentiveTurns > 0,
            onDelta: (delta) => {
              answer += delta
              setThinking(null)
              update({ content: answer })
            },
            onReplace: (replacement) => {
              answer = replacement
              update({ content: answer })
            },
            onPhase: (phase) => {
              if (phase.phase === "thinking") setThinking(phase.chars)
            },
            onMeta: (meta) => {
              update({ meta })
              if (meta.resources_shown) {
                void loadResources()
                // The session just escalated. Keep the next three turns careful:
                // a message after a hand-off is not ordinary small talk.
                setAttentiveTurns(3)
              } else if (meta.attentive) {
                setAttentiveTurns((current) => Math.max(0, current - 1))
              }
              if (meta.knowledge?.hits) {
                void api
                  .knowledgeSearch(history.at(-1)?.content ?? "", meta.knowledge.hits)
                  .then((result) => update({ sources: result.hits }))
                  .catch(() => undefined)
              }
            },
            onError: (message) => setError(message),
          },
        )
      } catch (err) {
        // A stopped answer is kept, not discarded: the user may have wanted
        // exactly the part that had already arrived.
        if (!controller.signal.aborted) {
          setError(err instanceof ApiError ? err.message : String(err))
          update({ content: answer })
        }
      } finally {
        abortRef.current = null
        setBusy(false)
        setThinking(null)
      }
    },
    [loadResources, useKnowledge, attentiveTurns],
  )

  const send = () => {
    const text = draft.trim()
    if (!text || busy) return
    setDraft("")
    const history: Message[] = [...messages, { role: "user", content: text }]
    void runTurn(history)
  }

  const stop = () => {
    abortRef.current?.abort()
    setBusy(false)
  }

  const regenerate = () => {
    if (busy) return
    const lastUser = [...messages].reverse().find((message) => message.role === "user")
    if (!lastUser) return
    const cut = messages.lastIndexOf(lastUser)
    // Keep everything up to and including the last user turn, so earlier
    // assistant replies stay in the context instead of being thrown away.
    void runTurn(messages.slice(0, cut + 1))
  }

  const copy = async (position: number, text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(position)
      window.setTimeout(() => setCopied(null), 1600)
    } catch {
      setCopied(null)
    }
  }

  const policyView = useMemo(
    () =>
      messages
        .map((message) => message.meta)
        .filter((meta): meta is StreamMeta => Boolean(meta))
        .at(-1),
    [messages],
  )

  const regionPack = useMemo(() => {
    if (!crisis) return null
    const region = (localStorage.getItem("hcs.region") ?? "DE").toUpperCase()
    return crisis.packs[region] ?? crisis.packs.EU ?? null
  }, [crisis])

  return (
    <>
      <SectionHeader as="h1" title={t(locale, "chatTitle")} description={t(locale, "chatLead")} />

      <div className="-mt-3 flex flex-wrap items-center gap-2">
        <Badge variant="secondary" className="max-w-full whitespace-normal text-left">
          {t(locale, "scope")}
        </Badge>
      </div>

      {policyView?.resources_shown && regionPack && (
        <div role="region" aria-label={t(locale, "crisisTitle")}>
          <Card className="border-pop-red-border bg-pop-red-surface">
            <CardContent className="flex flex-col gap-2 pt-6">
              <h2 className="flex items-center gap-2 text-base font-semibold text-pop-red-ink">
                <span aria-hidden="true">⚠</span>
                {t(locale, "crisisTitle")}
              </h2>
              <p className="text-sm text-pop-red-ink">
                <span className="font-medium">{regionPack.label}:</span>{" "}
                {regionPack.emergency.contact}
                {regionPack.lines.map((line) => ` · ${line.name}: ${line.contact}`).join("")}
              </p>
              {/* Full-opacity ink: at 80 % this line measured 4.26:1 against the
                  crisis surface, below the 4.5:1 AA floor for 12 px text. */}
              <p className="text-xs text-pop-red-ink">{t(locale, "crisisNote")}</p>
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="min-h-[48svh]">
        <CardContent className="flex flex-col gap-4 pt-6">
          {messages.length === 0 && (
            <p className="text-sm text-muted-foreground">{t(locale, "chatEmpty")}</p>
          )}
          <div className="flex flex-col gap-4" aria-live="polite" aria-atomic="false">
            {messages.map((message, position) => (
              <div
                key={`${message.role}-${position}`}
                className={
                  message.role === "user"
                    ? "max-w-[85%] self-end rounded-[var(--radius-card)] bg-primary px-4 py-3 text-sm text-primary-foreground"
                    : "flex max-w-[92%] flex-col gap-2 self-start rounded-[var(--radius-card)] bg-muted px-4 py-3 text-sm sm:max-w-[85%]"
                }
              >
                {message.role === "assistant" && !message.content && busy ? (
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Spinner />
                    {thinking !== null
                      ? `${t(locale, "chatThinking")} (${thinking})`
                      : t(locale, "chatSending")}
                  </span>
                ) : message.role === "assistant" ? (
                  <RichText text={message.content} />
                ) : (
                  <p className="whitespace-pre-wrap break-words">{message.content}</p>
                )}

                {message.meta && (
                  <div className="flex flex-wrap items-center gap-2">
                    {message.meta.model_bypassed && (
                      <Badge variant="secondary">{t(locale, "chatBypassed")}</Badge>
                    )}
                    {message.meta.output_guard_ok === false && (
                      <Badge variant="destructive">{t(locale, "chatGuardTripped")}</Badge>
                    )}
                    {message.meta.knowledge?.citations_ok === false && (
                      <Badge variant="destructive">{t(locale, "chatUnverifiedCitation")}</Badge>
                    )}
                    {message.meta.register?.mixed && (
                      <Badge variant="destructive" title={message.meta.register.advice ?? ""}>
                        {t(locale, "chatRegisterMixed")}
                      </Badge>
                    )}
                    {typeof message.meta.ttft_ms === "number" && (
                      <span className="text-xs text-muted-foreground">
                        {t(locale, "chatLatency")} {(message.meta.ttft_ms / 1000).toFixed(2)} s
                      </span>
                    )}
                    {typeof message.meta.tokens_per_second === "number" && (
                      <span className="text-xs text-muted-foreground">
                        {message.meta.tokens_per_second.toFixed(1)}{" "}
                        {t(locale, "chatTokensPerSecond")}
                      </span>
                    )}
                  </div>
                )}

                {message.role === "assistant" && message.content && (
                  <div className="flex flex-wrap items-center gap-1">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => void copy(position, message.content)}
                      aria-label={t(locale, "chatCopy")}
                    >
                      {copied === position ? <Check /> : <Copy />}
                      <span className="ml-1 hidden sm:inline">
                        {copied === position ? t(locale, "chatCopied") : t(locale, "chatCopy")}
                      </span>
                    </Button>
                    {position === messages.length - 1 && !busy && (
                      <Button variant="ghost" size="sm" onClick={regenerate}>
                        <RefreshCw />
                        <span className="ml-1 hidden sm:inline">{t(locale, "chatRegenerate")}</span>
                      </Button>
                    )}
                  </div>
                )}

                {message.sources && message.sources.length > 0 && (
                  <details className="text-xs text-muted-foreground">
                    <summary className="cursor-pointer select-none">
                      {t(locale, "chatSources")} ({message.sources.length})
                    </summary>
                    <ul className="mt-1 space-y-1">
                      {message.sources.map((hit) => (
                        <li key={hit.citation}>
                          <span className="font-mono">{hit.citation}</span>{" "}
                          {hit.title ?? hit.source} · {hit.score.toFixed(2)}
                        </li>
                      ))}
                    </ul>
                  </details>
                )}
              </div>
            ))}
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

      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 text-xs text-muted-foreground">
          <Switch
            checked={useKnowledge}
            onCheckedChange={setUseKnowledge}
            aria-label={t(locale, "chatUseKnowledge")}
          />
          {t(locale, "chatUseKnowledge")}
        </label>
        <div className="flex items-end gap-2">
          <Textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            placeholder={t(locale, "chatPlaceholder")}
            rows={3}
            onKeyDown={(event) => {
              if (event.key === "Enter" && !event.shiftKey) {
                event.preventDefault()
                send()
              }
            }}
            aria-label={t(locale, "chatPlaceholder")}
          />
          {busy ? (
            <Button variant="destructive" onClick={stop}>
              <Square />
              <span className="ml-1">{t(locale, "chatStop")}</span>
            </Button>
          ) : (
            <Button onClick={send} disabled={!draft.trim()}>
              {t(locale, "chatSend")}
            </Button>
          )}
        </div>
        <p className="text-xs text-muted-foreground">
          Enter ↵ {t(locale, "chatSend")} · Shift+Enter {t(locale, "chatNewline")}
        </p>
      </div>
    </>
  )
}
