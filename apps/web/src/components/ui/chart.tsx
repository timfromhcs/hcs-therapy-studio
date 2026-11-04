import * as React from "react"
import * as RechartsPrimitive from "recharts"

import { cn } from "@/lib/utils"

import { floatingSurfaceBase } from "./_shared"

/*
 * Loam Chart: the plotting frame, plus the tooltip and legend that read it.
 *
 * A tooltip is a floating surface, so it takes the card tier of the radius
 * scale and the floating shadow token, exactly like a popover or a menu.
 * Grid lines, axis ticks and cursors all resolve to the warm border token,
 * so the chart furniture never competes with the series colours.
 */

/* Format: { THEME_NAME: CSS_SELECTOR } */
const THEMES = { light: "", dark: ".dark" } as const

/** One of the two themes a chart series can carry its own colour for. */
type ChartTheme = keyof typeof THEMES

const THEME_NAMES: readonly ChartTheme[] = ["light", "dark"]

/**
 * Describes each series in a chart: its human label, an optional icon, and
 * either one colour or a light and dark pair. The keys become the
 * `--color-<key>` custom properties the chart marks read.
 */
export type ChartConfig = {
  [k in string]: {
    label?: React.ReactNode
    icon?: React.ComponentType
  } & (
    | { color?: string; theme?: never }
    | { color?: never; theme: Record<ChartTheme, string> }
  )
}

/**
 * One row of chart data as Recharts hands it back. A field either names a
 * category, and then holds a string, or carries a measure, and then holds a
 * number.
 */
type ChartRow = { [field: string]: string | number | null | undefined }

/** A style object that also carries a chart mark's own custom properties. */
type ChartVarStyle = React.CSSProperties &
  Record<`--${string}`, string | undefined>

type ChartContextProps = {
  config: ChartConfig
}

const ChartContext = React.createContext<ChartContextProps | null>(null)

function useChart() {
  const context = React.useContext(ChartContext)

  if (!context) {
    throw new Error("useChart must be used within a <ChartContainer />")
  }

  return context
}

/**
 * Wraps a Recharts chart, publishes the config to the tooltip and legend, and
 * maps every default Recharts stroke onto the Loam border and muted tokens.
 */
function ChartContainer({
  id,
  className,
  children,
  config,
  ...props
}: React.ComponentProps<"div"> & {
  config: ChartConfig
  children: React.ComponentProps<
    typeof RechartsPrimitive.ResponsiveContainer
  >["children"]
}) {
  const uniqueId = React.useId()
  const chartId = `chart-${id || uniqueId.replace(/:/g, "")}`

  return (
    <ChartContext.Provider value={{ config }}>
      <div
        data-slot="chart"
        data-chart={chartId}
        className={cn(
          "flex aspect-video justify-center text-xs",
          "[&_.recharts-cartesian-axis-tick_text]:fill-muted-foreground",
          "[&_.recharts-cartesian-grid_line[stroke='#ccc']]:stroke-border",
          "[&_.recharts-curve.recharts-tooltip-cursor]:stroke-border",
          "[&_.recharts-dot[stroke='#fff']]:stroke-transparent",
          "[&_.recharts-layer]:outline-hidden",
          "[&_.recharts-polar-grid_[stroke='#ccc']]:stroke-border",
          "[&_.recharts-radial-bar-background-sector]:fill-muted",
          "[&_.recharts-rectangle.recharts-tooltip-cursor]:fill-muted",
          "[&_.recharts-reference-line_[stroke='#ccc']]:stroke-border",
          "[&_.recharts-sector]:outline-hidden",
          "[&_.recharts-sector[stroke='#fff']]:stroke-transparent",
          "[&_.recharts-surface]:outline-hidden",
          className
        )}
        {...props}
      >
        <ChartStyle id={chartId} config={config} />
        <RechartsPrimitive.ResponsiveContainer>
          {children}
        </RechartsPrimitive.ResponsiveContainer>
      </div>
    </ChartContext.Provider>
  )
}

function ChartStyle({ id, config }: { id: string; config: ChartConfig }) {
  const colorConfig = Object.entries(config).filter(
    ([, entry]) => entry.theme || entry.color
  )

  if (!colorConfig.length) {
    return null
  }

  return (
    <style
      dangerouslySetInnerHTML={{
        __html: THEME_NAMES.map(
          (theme) => `
${THEMES[theme]} [data-chart=${id}] {
${colorConfig
  .map(([key, itemConfig]) => {
    const color = itemConfig.theme?.[theme] || itemConfig.color
    return color ? `  --color-${key}: ${color};` : null
  })
  .join("\n")}
}
`
        ).join("\n"),
      }}
    />
  )
}

/** The Recharts tooltip trigger. Pass `content` a `<ChartTooltipContent />`. */
const ChartTooltip = RechartsPrimitive.Tooltip

/**
 * The tooltip surface: a small floating card that resolves each series name,
 * colour and icon through the chart config.
 */
function ChartTooltipContent({
  active,
  payload,
  className,
  indicator = "dot",
  hideLabel = false,
  hideIndicator = false,
  label,
  labelFormatter,
  labelClassName,
  formatter,
  color,
  nameKey,
  labelKey,
}: React.ComponentProps<typeof RechartsPrimitive.Tooltip> &
  React.ComponentProps<"div"> & {
    hideLabel?: boolean
    hideIndicator?: boolean
    indicator?: "line" | "dot" | "dashed"
    nameKey?: string
    labelKey?: string
  }) {
  const { config } = useChart()

  const tooltipLabel = React.useMemo(() => {
    if (hideLabel || !payload?.length) {
      return null
    }

    const [item] = payload
    const row: ChartRow | undefined = item?.payload
    const key = `${labelKey || item?.dataKey || item?.name || "value"}`
    const itemConfig = getSeriesConfig(config, row, key)
    const value =
      !labelKey && isCategoryName(label)
        ? config[label]?.label || label
        : itemConfig?.label

    if (labelFormatter) {
      return (
        <div className={cn("font-semibold text-foreground", labelClassName)}>
          {labelFormatter(value, payload)}
        </div>
      )
    }

    if (!value) {
      return null
    }

    return (
      <div className={cn("font-semibold text-foreground", labelClassName)}>
        {value}
      </div>
    )
  }, [
    label,
    labelFormatter,
    payload,
    hideLabel,
    labelClassName,
    config,
    labelKey,
  ])

  if (!active || !payload?.length) {
    return null
  }

  const nestLabel = payload.length === 1 && indicator !== "dot"

  return (
    <div
      className={cn(
        floatingSurfaceBase,
        "grid min-w-36 items-start gap-1.5 px-4 py-3 text-xs",
        className
      )}
    >
      {!nestLabel ? tooltipLabel : null}
      <div className="grid gap-1.5">
        {payload.map((item, index) => {
          const row: ChartRow | undefined = item.payload
          const key = `${nameKey || item.name || item.dataKey || "value"}`
          const itemConfig = getSeriesConfig(config, row, key)
          const indicatorColor =
            color ?? readCategory(row, "fill") ?? item.color
          const indicatorStyle: ChartVarStyle = {
            "--color-bg": indicatorColor,
            "--color-border": indicatorColor,
          }

          return (
            <div
              key={`${item.dataKey ?? item.name ?? index}`}
              className={cn(
                "flex w-full flex-wrap items-stretch gap-2",
                "[&>svg]:size-2.5 [&>svg]:text-muted-foreground",
                indicator === "dot" && "items-center"
              )}
            >
              {formatter && item?.value !== undefined && item.name ? (
                formatter(item.value, item.name, item, index, item.payload)
              ) : (
                <>
                  {itemConfig?.icon ? (
                    <itemConfig.icon />
                  ) : (
                    !hideIndicator && (
                      <div
                        className={cn(
                          "shrink-0 rounded-full bg-(--color-bg) border-(--color-border)",
                          indicator === "dot" && "size-2.5",
                          indicator === "line" && "w-1",
                          indicator === "dashed" &&
                            "w-0 border-2 border-dashed bg-transparent",
                          nestLabel && indicator === "dashed" && "my-0.5"
                        )}
                        style={indicatorStyle}
                      />
                    )
                  )}
                  <div
                    className={cn(
                      "flex flex-1 justify-between leading-none",
                      nestLabel ? "items-end" : "items-center"
                    )}
                  >
                    <div className="grid gap-1.5">
                      {nestLabel ? tooltipLabel : null}
                      <span className="text-muted-foreground">
                        {itemConfig?.label || item.name}
                      </span>
                    </div>
                    {item.value !== undefined && item.value !== null && (
                      <span className="font-mono font-semibold tabular-nums text-foreground">
                        {item.value.toLocaleString()}
                      </span>
                    )}
                  </div>
                </>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

/** The Recharts legend trigger. Pass `content` a `<ChartLegendContent />`. */
const ChartLegend = RechartsPrimitive.Legend

/**
 * The legend row: one warm pill swatch, or the series icon, beside each label
 * resolved from the chart config.
 */
const ChartLegendContent = ({
  className,
  hideIcon = false,
  payload,
  verticalAlign = "bottom",
  nameKey,
}: React.ComponentProps<"div"> &
  Pick<RechartsPrimitive.LegendProps, "payload" | "verticalAlign"> & {
    hideIcon?: boolean
    nameKey?: string
  }) => {
  const { config } = useChart()

  if (!payload?.length) {
    return null
  }

  return (
    <div
      className={cn(
        "flex items-center justify-center gap-4",
        verticalAlign === "top" ? "pb-3" : "pt-3",
        className
      )}
    >
      {payload.map((item, index) => {
        const row: ChartRow | undefined = item.payload
        const key = `${nameKey || item.dataKey || "value"}`
        const itemConfig = getSeriesConfig(config, row, key)

        return (
          <div
            key={`${item.value ?? item.dataKey ?? index}`}
            className={cn(
              "flex items-center gap-1.5",
              "[&>svg]:size-3 [&>svg]:text-muted-foreground"
            )}
          >
            {itemConfig?.icon && !hideIcon ? (
              <itemConfig.icon />
            ) : (
              <div
                className="size-2 shrink-0 rounded-full"
                style={{ backgroundColor: item.color }}
              />
            )}
            {itemConfig?.label}
          </div>
        )
      })}
    </div>
  )
}
ChartLegendContent.displayName = "ChartLegendContent"

/** True when a chart field names a category instead of carrying a measure. */
function isCategoryName(
  field: string | number | null | undefined
): field is string {
  return typeof field === "string"
}

/** Reads one field off a chart row, but only when it names a category. */
function readCategory(
  row: ChartRow | undefined,
  field: string
): string | undefined {
  const value = row?.[field]
  return isCategoryName(value) ? value : undefined
}

/**
 * Finds the config entry for one series: by the category name the row holds
 * under `key` where there is one, so `nameKey="browser"` resolves
 * `config.chrome`, and by `key` itself otherwise.
 */
function getSeriesConfig(
  config: ChartConfig,
  row: ChartRow | undefined,
  key: string
) {
  const configKey = readCategory(row, key) ?? key
  return configKey in config ? config[configKey] : config[key]
}

export {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  ChartLegend,
  ChartLegendContent,
}
