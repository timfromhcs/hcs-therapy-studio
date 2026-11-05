/**
 * `@hcsmedia/therapy-sdk` — a typed client for the HCS Therapy Studio loopback API.
 *
 * The studio itself runs on the user's machine. This package is only the wire
 * format: it does not contain a model, does not call the network on its own, and
 * has no Node built-ins, so it works in a browser, an editor extension, or a
 * local script.
 */

export { HcsApiError, HcsClient, createClient } from "./client.js"
export type { HcsClientOptions, JournalInput } from "./client.js"
export type * from "./types.js"
