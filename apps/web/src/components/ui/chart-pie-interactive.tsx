import * as React from "react"
import { Pie, PieChart, Sector } from "recharts"
import type { PieSectorDataItem } from "recharts/types/polar/Pie"

import { cn } from "@/lib/utils"

import { pressSpring } from "./_shared"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "./card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
  type ChartConfig,
} from "./chart"

/*
 * A donut chart whose active slice is picked with Loam pills.
 *
 * The pills take the control tier, and the selected one wears the same flat
 * primary fill as the hero button, so the control set stays one material.
 */

/** Short label the showcase prints beside this block. */
export const description = "An interactive pie chart"

const chartData = [
  { browser: "chrome", visitors: 275, fill: "var(--color-chrome)" },
  { browser: "safari", visitors: 200, fill: "var(--color-safari)" },
  { browser: "firefox", visitors: 187, fill: "var(--color-firefox)" },
  { browser: "edge", visitors: 173, fill: "var(--color-edge)" },
  { browser: "other", visitors: 90, fill: "var(--color-other)" },
]

const chartConfig = {
  visitors: {
    label: "Visitors",
  },
  chrome: {
    label: "Chrome",
    color: "var(--chart-1)",
  },
  safari: {
    label: "Safari",
    color: "var(--chart-2)",
  },
  firefox: {
    label: "Firefox",
    color: "var(--chart-3)",
  },
  edge: {
    label: "Edge",
    color: "var(--chart-4)",
  },
  other: {
    label: "Other",
    color: "var(--chart-5)",
  },
} satisfies ChartConfig

/** A donut with one slice pulled out, chosen from a row of pills. */
export function ChartPieInteractive() {
  const [activeBrowser, setActiveBrowser] = React.useState(
    chartData[0].browser
  )

  const activeIndex = React.useMemo(
    () => chartData.findIndex((item) => item.browser === activeBrowser),
    [activeBrowser]
  )

  return (
    <Card className="flex flex-col">
      <CardHeader className="items-center pb-0">
        <CardTitle>Pie Chart - Interactive</CardTitle>
        <CardDescription>January - June 2024</CardDescription>
      </CardHeader>
      <CardContent className="flex-1 pb-0">
        <div className="flex flex-wrap justify-center gap-1.5 pb-2">
          {chartData.map((item) => (
            <button
              key={item.browser}
              type="button"
              aria-pressed={activeBrowser === item.browser}
              onClick={() => setActiveBrowser(item.browser)}
              className={cn(
                "rounded-[var(--radius-control)] border px-3 py-1.5 text-xs font-semibold",
                "transition-colors duration-fast ease-out",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-background",
                pressSpring,
                activeBrowser === item.browser
                  ? "border-primary bg-primary text-primary-foreground [box-shadow:var(--shadow-xs)]"
                  : "border-border bg-card text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {chartConfig[item.browser as keyof typeof chartConfig]?.label}
            </button>
          ))}
        </div>
        <ChartContainer
          config={chartConfig}
          className="mx-auto aspect-square max-h-64"
        >
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Pie
              data={chartData}
              dataKey="visitors"
              nameKey="browser"
              innerRadius={60}
              activeIndex={activeIndex}
              activeShape={({
                outerRadius = 0,
                ...props
              }: PieSectorDataItem) => (
                <Sector {...props} outerRadius={outerRadius + 10} />
              )}
            />
          </PieChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
