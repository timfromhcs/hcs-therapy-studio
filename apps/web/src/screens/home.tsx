import { useEffect, useState } from "react"

import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { SectionHeader } from "@/components/ui/section-header"
import { Spinner } from "@/components/ui/spinner"
import { StatCard } from "@/components/ui/stat-card"
import { api } from "@/lib/api"
import type { DeviceReport } from "@/lib/api"
import type { Locale } from "@/lib/i18n"
import { t } from "@/lib/i18n"

export function HomeScreen({
  locale,
  health,
}: {
  locale: Locale
  health: { connected: boolean; modelLoaded: boolean }
}) {
  const [report, setReport] = useState<DeviceReport | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    api
      .deviceProfile()
      .then((payload) => alive && setReport(payload))
      .catch((err: Error) => alive && setError(err.message))
    return () => {
      alive = false
    }
  }, [health.connected])

  return (
    <>
      <SectionHeader as="h1" title={t(locale, "homeTitle")} description={t(locale, "homeLead")} />

      {error && (
        <Alert>
          <AlertTitle>{t(locale, "disconnected")}</AlertTitle>
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {!report ? (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Spinner /> {t(locale, "commonLoading")}
        </div>
      ) : (
        <>
          {report.profile ? (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatCard
                label={t(locale, "profileLabel")}
                /* The enum has no space to wrap at; showing it with a space lets
                   it break into two tidy lines instead of mid-word. */
                value={report.profile.profile.replace(/_/g, " ")}
              />
              <StatCard
                label={t(locale, "contextLabel")}
                value={`${report.profile.context.toLocaleString()} tokens`}
              />
              <StatCard
                label={t(locale, "ramLabel")}
                value={`${report.hardware.ram_available_gib} GiB`}
                description={`${report.hardware.ram_total_gib} GiB total`}
              />
              <StatCard
                label={t(locale, "budgetLabel")}
                value={`${report.profile.budget_gib} GiB`}
                description={`${report.profile.estimated_runtime_gib} GiB estimated`}
              />
            </div>
          ) : (
            <Alert>
              <AlertTitle>{t(locale, "noProfile")}</AlertTitle>
            </Alert>
          )}

          {report.profile && (
            <Card>
              <CardHeader>
                <CardTitle>{t(locale, "reasonsTitle")}</CardTitle>
              </CardHeader>
              <CardContent>
                <ul className="flex flex-col gap-2 text-sm text-muted-foreground">
                  {report.profile.reasons.map((reason) => (
                    <li key={reason}>{reason}</li>
                  ))}
                </ul>
                {report.profile.warnings.length > 0 && (
                  <ul className="mt-4 flex flex-col gap-2 text-sm">
                    {report.profile.warnings.map((warning) => (
                      <li key={warning} className="text-pop-orange-ink">
                        {warning}
                      </li>
                    ))}
                  </ul>
                )}
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle>{t(locale, "deviceTitle")}</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="grid gap-3 text-sm sm:grid-cols-2">
                <div>
                  <dt className="text-muted-foreground">CPU</dt>
                  <dd>{report.hardware.cpu_name}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">GPU</dt>
                  <dd>{report.hardware.gpus.map((gpu) => gpu.name).join(", ") || "—"}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Vulkan</dt>
                  <dd>
                    {report.hardware.vulkan.usable
                      ? report.hardware.vulkan.devices
                          .map((device) => `${device.name} · ${device.api_version}`)
                          .join(", ")
                      : (report.hardware.vulkan.error ?? "—")}
                  </dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">OS</dt>
                  <dd>
                    {report.hardware.os_name} {report.hardware.os_version}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </>
      )}
    </>
  )
}
