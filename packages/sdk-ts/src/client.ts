import type {
  AuditEvent,
  ChatRequest,
  ChatResult,
  DeviceReport,
  ExportResult,
  HealthInfo,
  JournalEntry,
  KnowledgeDocument,
  KnowledgeSearch,
  KnowledgeStats,
  ModelInfo,
  Resources,
  StorageUsage,
  StreamHandlers,
  VersionInfo,
  WipeResult,
} from "./types.js"

/**
 * The API rejected the request. `status` is the HTTP status so a caller can
 * distinguish "you forgot the token" from "the model is not running".
 */
export class HcsApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = "HcsApiError"
    this.status = status
  }
}

export interface HcsClientOptions {
  /** Per-launch bearer token printed by `hcs-therapy serve`. */
  token: string
  /** Defaults to `http://127.0.0.1:8765`. Non-loopback hosts are refused by the server. */
  baseUrl?: string
  /** Injected for tests and for runtimes without a global `fetch`. */
  fetchImpl?: typeof fetch
}

export interface JournalInput {
  body: string
  title?: string | null
  mood?: number | null
  tags?: string[]
}

const DEFAULT_BASE = "http://127.0.0.1:8765"

/**
 * Typed client for the local studio API.
 *
 * Two properties matter and are enforced by the server, not by this class:
 * every mutating call carries an explicit `confirmed: true`, and the token is
 * sent as a bearer header rather than a query parameter so it cannot end up in a
 * proxy log.
 */
export class HcsClient {
  private readonly baseUrl: string
  private readonly token: string
  private readonly fetchImpl: typeof fetch

  constructor(options: HcsClientOptions) {
    if (!options.token) {
      throw new Error(
        "a token is required; start `hcs-therapy serve` and read the token it prints",
      )
    }
    this.token = options.token
    this.baseUrl = (options.baseUrl ?? DEFAULT_BASE).replace(/\/+$/, "")
    this.fetchImpl = options.fetchImpl ?? globalThis.fetch
  }

  private headers(extra: Record<string, string> = {}): Record<string, string> {
    return {
      Authorization: `Bearer ${this.token}`,
      "Content-Type": "application/json",
      ...extra,
    }
  }

  private async request<T>(
    path: string,
    init: { method?: string; body?: unknown } = {},
  ): Promise<T> {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: init.method ?? "GET",
      headers: this.headers(),
      body: init.body === undefined ? undefined : JSON.stringify(init.body),
    })
    const text = await response.text()
    let payload: unknown = null
    if (text) {
      try {
        payload = JSON.parse(text)
      } catch {
        payload = { error: text.slice(0, 300) }
      }
    }
    if (!response.ok) {
      const message =
        payload && typeof payload === "object" && "error" in payload
          ? String((payload as { error: unknown }).error)
          : `HTTP ${response.status}`
      throw new HcsApiError(message, response.status)
    }
    return payload as T
  }

  // -- read-only -----------------------------------------------------------

  /** Liveness. Needs no token and returns no user data. */
  health(): Promise<HealthInfo> {
    return this.request<HealthInfo>("/health")
  }

  version(): Promise<VersionInfo> {
    return this.request<VersionInfo>("/version")
  }

  deviceProfile(): Promise<DeviceReport> {
    return this.request<DeviceReport>("/api/device/profile")
  }

  models(): Promise<{ models: ModelInfo[] }> {
    return this.request<{ models: ModelInfo[] }>("/api/models")
  }

  storage(): Promise<StorageUsage> {
    return this.request<StorageUsage>("/api/storage/usage")
  }

  audit(): Promise<{ events: AuditEvent[] }> {
    return this.request<{ events: AuditEvent[] }>("/api/audit")
  }

  resources(): Promise<Resources> {
    return this.request<Resources>("/api/safety/resources")
  }

  journal(): Promise<{ entries: JournalEntry[] }> {
    return this.request<{ entries: JournalEntry[] }>("/api/journal")
  }

  // -- knowledge -----------------------------------------------------------

  knowledgeStats(): Promise<KnowledgeStats> {
    return this.request<KnowledgeStats>("/api/knowledge/stats")
  }

  knowledgeDocuments(): Promise<{ documents: KnowledgeDocument[] }> {
    return this.request<{ documents: KnowledgeDocument[] }>("/api/knowledge/documents")
  }

  /** Hybrid lexical search. `lambda` is the MMR relevance weight (0..1). */
  knowledgeSearch(query: string, options: { k?: number; lambda?: number } = {}) {
    const params = new URLSearchParams({
      q: query,
      k: String(options.k ?? 5),
      lambda: String(options.lambda ?? 0.7),
    })
    return this.request<KnowledgeSearch>(`/api/knowledge/search?${params.toString()}`)
  }

  /** Re-index the journal. Requires the explicit confirmation flag by design. */
  knowledgeReindex(): Promise<{ indexed: number; stats: KnowledgeStats }> {
    return this.request("/api/knowledge/reindex", {
      method: "POST",
      body: { confirmed: true },
    })
  }

  // -- writes (all confirmed) ---------------------------------------------

  createJournal(input: JournalInput): Promise<{ id: string }> {
    return this.request("/api/journal", {
      method: "POST",
      body: { ...input, confirmed: true },
    })
  }

  deleteJournal(id: string): Promise<{ deleted: string }> {
    return this.request(`/api/journal/${encodeURIComponent(id)}`, {
      method: "DELETE",
      body: { confirmed: true },
    })
  }

  exportData(): Promise<ExportResult> {
    return this.request("/api/data/export", {
      method: "POST",
      body: { confirmed: true },
    })
  }

  wipeData(): Promise<WipeResult> {
    return this.request("/api/data/wipe", {
      method: "POST",
      body: { confirmed: true },
    })
  }

  // -- chat ----------------------------------------------------------------

  async chat(request: ChatRequest): Promise<ChatResult> {
    const payload = await this.request<{
      choices?: { message?: { content?: string } }[]
      hcs: ChatResult["meta"]
    }>("/v1/chat/completions", { method: "POST", body: request })
    return {
      content: payload.choices?.[0]?.message?.content ?? "",
      meta: payload.hcs,
      raw: payload,
    }
  }

  /**
   * Streamed chat over server-sent events.
   *
   * Aborting the signal closes the socket; whatever arrived before the abort
   * stays with the caller, so a stopped answer is kept rather than discarded.
   * The crisis gate has already run by the time the first event arrives.
   */
  async chatStream(request: ChatRequest, handlers: StreamHandlers = {}): Promise<void> {
    const response = await this.fetchImpl(`${this.baseUrl}/v1/chat/completions`, {
      method: "POST",
      headers: this.headers(),
      body: JSON.stringify({ ...request, stream: true }),
      signal: handlers.signal,
    })
    if (!response.ok) {
      const text = await response.text()
      throw new HcsApiError(text.slice(0, 300) || `HTTP ${response.status}`, response.status)
    }
    if (!response.body) throw new HcsApiError("this runtime cannot read a stream", 0)

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ""

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      let newline = buffer.indexOf("\n")
      while (newline >= 0) {
        const line = buffer.slice(0, newline).trimEnd()
        buffer = buffer.slice(newline + 1)
        newline = buffer.indexOf("\n")
        if (!line.startsWith("data:")) continue
        let payload: Record<string, unknown>
        try {
          payload = JSON.parse(line.slice(5).trim()) as Record<string, unknown>
        } catch {
          continue
        }
        if (typeof payload.delta === "string") handlers.onDelta?.(payload.delta)
        else if (typeof payload.replace === "string") handlers.onReplace?.(payload.replace)
        else if (typeof payload.phase === "string")
          handlers.onPhase?.({ phase: payload.phase, chars: Number(payload.chars ?? 0) })
        else if (typeof payload.error === "string") handlers.onError?.(payload.error)
        else if (typeof payload.policy_mode === "string")
          handlers.onMeta?.(payload as unknown as ChatResult["meta"])
      }
    }
  }
}

export function createClient(options: HcsClientOptions): HcsClient {
  return new HcsClient(options)
}
