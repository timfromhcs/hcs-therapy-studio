/**
 * Public types for the HCS Therapy Studio loopback API.
 *
 * These mirror the payloads the Python side actually returns. Where the server
 * can return `null`, the type says `null` instead of widening to optional: a
 * missing value and a null value are different bugs in a UI.
 */

/** Every response carries the product credit; it is part of the contract. */
export interface VersionInfo {
  version: string
  product: string
  credit: string
  api: number
}

export interface HealthInfo {
  status: "ok" | string
  version: string
  local_only: true
  model_loaded: boolean
}

export interface GpuInfo {
  name: string
  driver_version?: string | null
}

export interface VulkanDevice {
  name: string
  device_type: string
  api_version: string
}

export interface VulkanInfo {
  loader_present: boolean
  usable: boolean
  error: string | null
  devices: VulkanDevice[]
}

export interface HardwareInfo {
  os_name: string
  os_version: string
  os_build?: string
  architecture: string
  cpu_name: string
  cpu_cores: number
  ram_total_gib: number
  ram_available_gib: number
  gpus: GpuInfo[]
  vulkan: VulkanInfo
  redacted: boolean
}

/** The compute profile the detector chose, and the reasons it chose it. */
export interface ProfileDecision {
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

export interface DeviceReport {
  hardware: HardwareInfo
  profile: ProfileDecision | null
}

export interface ModelInfo {
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

export interface StorageUsage {
  models_bytes: number
  models_count: number
  root: string
}

export interface AuditEvent {
  created_at: string
  event: string
  tool: string | null
  status: string
  summary: string
}

export interface JournalEntry {
  id: string
  title: string | null
  body: string
  mood: number | null
  tags: string[]
  created_at: string
  updated_at: string
}

export interface VerifiedResource {
  name: string
  contact: string
  hours: string
  source_url: string
  verified: boolean
}

export interface RegionPack {
  label: string
  emergency: { name: string; contact: string; verified: boolean }
  lines: VerifiedResource[]
  reviewed_at: string
}

export interface Resources {
  reviewed_at: string
  packs: Record<string, RegionPack>
  unknown: { label: string; emergency: string; note: string | null }
}

/** Where an address form the German reply used came from. */
export interface RegisterInfo {
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

export interface KnowledgeStats {
  documents: number
  chunks: number
  path: string
  encrypted: boolean
  retriever: string
  /** Always `null` in this build: no embedding model is installed. */
  vector_index: null
  note: string
}

export interface KnowledgeHit {
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

export interface KnowledgeSearch {
  query: string
  hits: KnowledgeHit[]
  retriever: string
  empty_reason: string | null
}

export interface KnowledgeDocument {
  doc_id: string
  source: string
  title: string | null
  chunk_count: number
  indexed_at?: string
}

/** The `hcs` envelope the chat endpoint attaches to every answer. */
export interface ChatMeta {
  policy_mode: "normal" | "crisis_imminent" | "crisis_supportive"
  resources_shown: boolean
  scope_label: string
  model_bypassed: boolean
  output_guard_ok?: boolean
  output_guard_categories?: string[]
  register?: RegisterInfo
  attentive?: boolean
  ttft_ms?: number | null
  first_activity_ms?: number | null
  tokens_per_second?: number | null
  reasoning_chars?: number
  streamed?: boolean
  stream_error?: string
  original_flagged?: boolean
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

export interface ChatMessage {
  role: "system" | "user" | "assistant"
  content: string
}

export interface ChatRequest {
  messages: ChatMessage[]
  max_tokens?: number
  temperature?: number
  top_p?: number
  stream?: boolean
  hcs?: {
    use_knowledge?: boolean
    knowledge_k?: number
    region?: string
    locale?: "de" | "en" | string
    attentive?: boolean
    no_register_anchor?: boolean
  }
}

export interface ChatResult {
  content: string
  meta: ChatMeta
  raw: unknown
}

export interface StreamHandlers {
  onDelta?: (delta: string) => void
  onMeta?: (meta: ChatMeta) => void
  onPhase?: (phase: { phase: string; chars: number }) => void
  onReplace?: (text: string) => void
  onError?: (message: string) => void
  signal?: AbortSignal
}

export interface ExportResult {
  path: string
}

export interface WipeResult {
  deleted: Record<string, number>
}
