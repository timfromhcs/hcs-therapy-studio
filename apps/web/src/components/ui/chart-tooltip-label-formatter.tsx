"use client"

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
 * A tooltip that rewrites its own heading.
 *
 * The tooltip is a floating surface, so it takes the card tier of the radius
 * scale and the floating shadow token, the same as a popover or a menu.
 */

/** Short label the showcase prints beside this block. */
export const description = "A tooltip with a formatted label"

const chartData = [
  { date: "2024-01-01", desktop: 186, mobile: 80 },
  { date: "2024-02-01", desktop: 305, mobile: 200 },
  { date: "2024-03-01", desktop: 237, mobile: 120 },
  { date: "2024-04-01", desktop: 73, mobile: 190 },
  { date: "2024-05-01", desktop: 209, mobile: 130 },
  { date: "2024-06-01", desktop: 214, mobile: 140 },
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

/** A tooltip whose heading turns the raw date into a readable month. */
export function ChartTooltipLabelFormatter() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Tooltip - Label Formatter</CardTitle>
        <CardDescription>January - June 2024</CardDescription>
      </CardHeader>
      <CardContent>
        <ChartContainer config={chartConfig}>
          <BarChart accessibilityLayer data={chartData}>
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="date"
              tickLine={false}
              tickMargin={10}
              axisLine={false}
              tickFormatter={(value) =>
                new Date(value).toLocaleDateString("en-US", { month: "short" })
              }
            />
            <ChartTooltip
              cursor={false}
              content={
                <ChartTooltipContent
                  labelFormatter={(_, payload) =>
                    new Date(
                      String(payload?.[0]?.payload?.date ?? "")
                    ).toLocaleDateString("en-US", {
                      month: "long",
                      year: "numeric",
                    })
                  }
                />
              }
            />
            <Bar dataKey="desktop" fill="var(--color-desktop)" radius={4} />
            <Bar dataKey="mobile" fill="var(--color-mobile)" radius={4} />
          </BarChart>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
