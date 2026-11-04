"use client"

import * as React from "react"
import { Area, AreaChart, CartesianGrid, XAxis } from "recharts"

import {
  Card,
  CardAction,
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./select"

/*
 * An area chart whose visible range comes from a Loam Select.
 *
 * The block composes the design system's own Select rather than a bare
 * button row, so the control carries Loam's field recipe, its pill trigger
 * and its floating list for free, and the card around it stays on the card
 * tier.
 */

/** Short label the showcase prints beside this block. */
export const description = "An interactive area chart"

const chartData = [
  { month: "January", desktop: 186, mobile: 80 },
  { month: "February", desktop: 305, mobile: 200 },
  { month: "March", desktop: 237, mobile: 120 },
  { month: "April", desktop: 173, mobile: 190 },
  { month: "May", desktop: 209, mobile: 130 },
  { month: "June", desktop: 214, mobile: 140 },
]

const chartConfig = {
  desktop: {
    label: "Desktop",
    color: "var(--chart-1)",
  },
  mobile: {
    label: "Mobile",
    color: "var(--chart-2)",
  },
} satisfies ChartConfig

const ranges = [
  { value: "6", label: "Last 6 months" },
  { value: "3", label: "Last 3 months" },
  { value: "1", label: "Last month" },
] as const

/** Two stacked areas, with a Select that shortens the visible range. */
export function ChartAreaInteractive() {
  const [range, setRange] = React.useState("6")

  const visibleData = React.useMemo(
    () => chartData.slice(chartData.length - Number(range)),
    [range]
  )

  return (
    <Card>
      <CardHeader>
        <CardTitle className="whitespace-nowrap">Area Chart - Interactive</CardTitle>
        <CardDescription>
          Showing total visitors for the selected range
        </CardDescription>
        <CardAction>
          <Select value={range} onValueChange={(value) => value && setRange(value)}>
            <SelectTrigger className="w-44" aria-label="Select a range">
              <SelectValue placeholder="Last 6 months" />
            </SelectTrigger>
            <SelectContent>
              {ranges.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardAction>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={chartConfig}
          className="aspect-auto h-64 w-full"
        >
          <AreaChart
            accessibilityLayer
            data={visibleData}
            margin={{ left: 12, right: 12 }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={(value) => value.slice(0, 3)}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent indicator="dot" />}
            />
            <Area
              dataKey="mobile"
              type="natural"
              fill="var(--color-mobile)"
              fillOpacity={0.4}
              stroke="var(--color-mobile)"
              stackId="a"
            />
            <Area
              dataKey="desktop"
              type="natural"
              fill="var(--color-desktop)"
              fillOpacity={0.4}
              stroke="var(--color-desktop)"
              stackId="a"
            />
          </AreaChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
