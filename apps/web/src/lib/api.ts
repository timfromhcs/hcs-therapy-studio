/**
 * Typed client for the local HCS Therapy Studio API.
 *
 * Security notes that matter for the UI:
 * - the token is stored in localStorage only; it never leaves the machine,
 * - every request goes to 127.0.0.1 (the server rejects other origins),
 * - side-effecting calls send `confirmed: true` explicitly, so a stray click
 *   cannot delete a journal entry.
 */

export type ModelInfo = {
  id: string
  name: string
  publisher: string
  quantisation: string | null
  license_spdx: string
  license_url: string
  size_bytes: number
  approved: boolean
  installed: boolean
  installed_path: string | null
}

export type ProfileDecision = {
  profile: string
  backend: string
  n_gpu_layers: number
  context: number
  estimated_runtime_gib: number
  budget_gib: number
  kv_bytes_per_token: number
  device_name: string | null
  reasons: string[]
  warnings: string[]
}

export type DeviceReport = {
  hardware: {
    os_name: string
    os_version: string
    cpu_name: string
    cpu_cores: number
    ram_total_gib: number
    ram_available_gib: number
    gpus: { name: string }[]
    vulkan: {
      loader_present: boolean
      usable: boolean
      error: string | null
      devices: { name: string; device_type: string; api_version: string }[]
    }
    redacted: boolean
  }
  profile: ProfileDecision | null
}

export type JournalEntry = {
  id: string
  title: string | null
  body: string
  mood: number | null
  tags: string[]
  created_at: string
  updated_at: string
}

export type AuditEvent = {
  created_at: string
  event: string
  tool: string | null
  status: string
  summary: string
}

export type Resources = {
  reviewed_at: string
  packs: Record<
    string,
    {
      label: string
      emergency: { name: string; contact: string; verified: boolean }
      lines: { name: string; contact: string; hours: string; source_url: string; verified: boolean }[]
      reviewed_at: string
    }
  >
  unknown: { label: string; emergency: string; note: string | null }
}

export type ChatMeta = {
  policy_mode: "normal" | "crisis_imminent" | "crisis_supportive"
  resources_shown: boolean
  scope_label: string
  model_bypassed: boolean
  output_guard_ok?: boolean
  output_guard_categories?: string[]
}

export type ChatResult = {
  content: string
  meta: ChatMeta
}

export type StorageUsage = {
  models_bytes: number
  models_count: number
  root: string
}

export type KnowledgeHit = {
  chunk_id: number
  doc_id: string
  source: string
  title: string | null
  text: string
  score: number
  citation: string
  rank_word: number | null
  rank_trigram: number | null
}

export type KnowledgeStats = {
  documents: number
  chunks: number
  path: string
  encrypted: boolean
  retriever: string
  vector_index: null
  note: string
}

export type StreamMeta = ChatMeta & {
  ttft_ms?: number | null
  tokens_per_second?: number | null
  streamed?: boolean
  stream_error?: string
  attentive?: boolean
  register?: {
    register: "du" | "sie" | "neutral"
    label_de: string
    mixed: boolean
    du_forms: number
    sie_forms: number
    ambiguous_sie: number
    examples: Record<string, string[]>
    advice: string | null
    anchored: boolean
    violated_anchor: boolean
  }
  knowledge?: {
    requested: boolean
    hits: number
    chunk_ids: number[]
    citations_used?: number
    unverified_citations?: number[]
    citations_ok?: boolean
    empty_reason: string | null
  }
}

export class ApiError extends Error {
  status: number
  constructor(message: string, status: number) {
    super(message)
    this.status = status
  }
}

const TOKEN_KEY = "hcs.token"
const BASE_KEY = "hcs.baseUrl"

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) ?? ""
}

export function setToken(token: string): void {
  if (token) localStorage.setItem(TOKEN_KEY, token.trim())
  else localStorage.removeItem(TOKEN_KEY)
}

export function getBaseUrl(): string {
  return localStorage.getItem(BASE_KEY) ?? "http://127.0.0.1:8765"
}

export function setBaseUrl(url: string): void {
  localStorage.setItem(BASE_KEY, url.replace(/\/+$/, ""))
}

async function request<T>(
  path: string,
  options: { method?: string; body?: unknown } = {},
): Promise<T> {
  const token = getToken()
  const response = await fetch(`${getBaseUrl()}${path}`, {
    method: options.method ?? "GET",
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
  })
  const text = await response.text()
  let payload: unknown = null
  if (text) {
    try {
      payload = JSON.parse(text)
    } catch {
      payload = { error: text.slice(0, 200) }
    }
  }
  if (!response.ok) {
    const message =
      payload && typeof payload === "object" && "error" in payload
        ? String((payload as { error: unknown }).error)
        : `HTTP ${response.status}`
    throw new ApiError(message, response.status)
  }
  return payload as T
}

export const api = {
  health: () =>
    request<{ status: string; version: string; local_only: boolean; model_loaded: boolean }>(
      "/health",
    ),
  version: () => request<{ version: string; product: string; credit: string }>("/version"),
  deviceProfile: () => request<DeviceReport>("/api/device/profile"),
  models: () => request<{ models: ModelInfo[] }>("/api/models"),
  storage: () => request<StorageUsage>("/api/storage/usage"),
  audit: () => request<{ events: AuditEvent[] }>("/api/audit"),
  resources: () => request<Resources>("/api/safety/resources"),
  journal: () => request<{ entries: JournalEntry[] }>("/api/journal"),
  createJournal: (input: { body: string; title?: string; mood?: number; tags?: string[] }) =>
    request<{ id: string }>("/api/journal", {
      method: "POST",
      body: { ...input, confirmed: true },
    }),
  deleteJournal: (id: string) =>
    request<{ deleted: string }>(`/api/journal/${id}`, {
      method: "DELETE",
      body: { confirmed: true },
    }),
  exportData: () =>
    request<{ path: string }>("/api/data/export", { method: "POST", body: { confirmed: true } }),
  wipeData: () =>
    request<{ deleted: Record<string, number> }>("/api/data/wipe", {
      method: "POST",
      body: { confirmed: true },
    }),
  chat: async (messages: { role: string; content: string }[]): Promise<ChatResult> => {
    const payload = await request<{
      choices: { message: { content: string } }[]
      hcs: ChatMeta
    }>("/v1/chat/completions", {
      method: "POST",
      body: {
        messages,
        hcs: {
          region: (localStorage.getItem("hcs.region") ?? "").toUpperCase(),
          locale: (localStorage.getItem("hcs.locale") ?? "").slice(0, 2),
        },
      },
    })
    return {
      content: payload.choices?.[0]?.message?.content ?? "",
      meta: payload.hcs,
    }
  },

  /**
   * Streaming chat over the server's SSE endpoint.
   *
   * On stop the AbortController aborts the fetch, which closes the socket; the
   * server treats that as a normal client hang-up and writes nothing further.
   * Whatever arrived before the abort stays in the caller's buffer, so a stopped
   * answer is kept, never corrupted.
   */
  chatStream: async (
    messages: { role: string; content: string }[],
    handlers: {
      onDelta: (delta: string) => void
      onMeta: (meta: StreamMeta) => void
      onPhase?: (phase: { phase: string; chars: number }) => void
      onReplace?: (text: string) => void
      onError?: (message: string) => void
      signal?: AbortSignal
      useKnowledge?: boolean
      attentive?: boolean
    },
  ): Promise<void> => {
    const token = getToken()
    const response = await fetch(`${getBaseUrl()}/v1/chat/completions`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({
        messages,
        stream: true,
        hcs: {
          ...(handlers.useKnowledge ? { use_knowledge: true } : {}),
          ...(handlers.attentive ? { attentive: true } : {}),
          region: (localStorage.getItem("hcs.region") ?? "").toUpperCase(),
          locale: (localStorage.getItem("hcs.locale") ?? "").slice(0, 2),
        },
      }),
      signal: handlers.signal,
    })
    if (!response.ok) {
      const text = await response.text()
      throw new ApiError(text.slice(0, 300) || `HTTP ${response.status}`, response.status)
    }
    if (!response.body) throw new ApiError("this browser cannot read a stream", 0)

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
          payload = JSON.parse(line.slice(5).trim())
        } catch {
          continue
        }
        if (typeof payload.delta === "string") handlers.onDelta(payload.delta)
        else if (typeof payload.replace === "string") handlers.onReplace?.(payload.replace)
        else if (typeof payload.phase === "string")
          handlers.onPhase?.({
            phase: payload.phase,
            chars: Number(payload.chars ?? 0),
          })
        else if (typeof payload.error === "string") handlers.onError?.(payload.error)
        else if (typeof payload.policy_mode === "string")
          handlers.onMeta(payload as unknown as StreamMeta)
      }
    }
  },

  knowledgeStats: () => request<KnowledgeStats>("/api/knowledge/stats"),
  knowledgeDocuments: () =>
    request<{ documents: { doc_id: string; source: string; title: string | null; chunk_count: number }[] }>(
      "/api/knowledge/documents",
    ),
  knowledgeSearch: (query: string, k = 5, lambda = 0.7) =>
    request<{ query: string; hits: KnowledgeHit[]; retriever: string; empty_reason: string | null }>(
      `/api/knowledge/search?q=${encodeURIComponent(query)}&k=${k}&lambda=${lambda}`,
    ),
  knowledgeReindex: () =>
    request<{ indexed: number; stats: KnowledgeStats }>("/api/knowledge/reindex", {
      method: "POST",
      body: { confirmed: true },
    }),
}
