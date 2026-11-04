import * as React from "react"
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts"

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
 * A tooltip that adds its own unit and a total row.
 *
 * The total sits above a hairline in the border token, so the extra row reads
 * as part of the same floating card rather than as a second panel.
 */

/** Short label the showcase prints beside this block. */
export const description = "A tooltip with a total row"

const chartData = [
  { activity: "Monday", running: 450, swimming: 300 },
  { activity: "Tuesday", running: 380, swimming: 420 },
  { activity: "Wednesday", running: 520, swimming: 120 },
  { activity: "Thursday", running: 140, swimming: 550 },
  { activity: "Friday", running: 600, swimming: 350 },
  { activity: "Saturday", running: 480, swimming: 500 },
]

const chartConfig = {
  running: {
    label: "Running",
    color: "var(--chart-1)",
  },
  swimming: {
    label: "Swimming",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig

/** A tooltip that labels each value in kcal and sums the two series. */
export function ChartTooltipAdvanced() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tooltip - Advanced</CardTitle>
        <CardDescription>Calories burned this week</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart accessibilityLayer data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="activity"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tickFormatter={(value) => value.slice(0, 3)}
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  hideLabel
                  className="w-44"
                  formatter={(value, name, item, index) => (
                    <>
                      <div
                        className="size-2.5 shrink-0 rounded-full bg-(--color-bg)"
                        style={
                          {
                            "--color-bg": `var(--color-${name})`,
                          } as React.CSSProperties
                        }
                      />
                      {chartConfig[name as keyof typeof chartConfig]?.label ||
                        name}
                      <div className="ml-auto flex items-baseline gap-0.5 font-mono font-semibold tabular-nums text-foreground">
                        {value}
                        <span className="font-normal text-muted-foreground">
                          kcal
                        </span>
                      </div>
                      {index === 1 && (
                        <div className="mt-1.5 flex basis-full items-center border-t border-border pt-1.5 text-xs font-semibold text-foreground">
                          Total
                          <div className="ml-auto flex items-baseline gap-0.5 font-mono font-semibold tabular-nums text-foreground">
                            {item.payload.running + item.payload.swimming}
                            <span className="font-normal text-muted-foreground">
                              kcal
                            </span>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                />
              }
            />
            <Bar dataKey="running" fill="var(--color-running)" radius={4} />
            <Bar dataKey="swimming" fill="var(--color-swimming)" radius={4} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
