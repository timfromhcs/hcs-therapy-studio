import * as React from "react"
import {
  ArrowDown,
  ArrowUp,
  ChevronLeft,
  ChevronRight,
  ChevronsUpDown,
} from "lucide-react"

import { cn } from "@/lib/utils"
import { Button } from "./button"
import {
  Table,
  TableBody,
  TableCaption,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "./table"

/*
 * Loam DataTable: the card-tier Table with sorting and paging added.
 *
 * It composes the Loam Table, so the white squircle and the warm hairline stay
 * in one place. Sorting and paging are plain React state, because this system
 * carries no table engine dependency.
 */

/** One column of a Loam data table: how to label it, read it and sort it. */
export interface DataTableColumn<TRow> {
  /** Stable key for the column, used for the sort state and the React key. */
  id: string
  header: React.ReactNode
  /** Reads the cell content out of a row. */
  cell: (row: TRow) => React.ReactNode
  /** Supply this to make the column sortable, returning the value to compare. */
  sortValue?: (row: TRow) => string | number
  /** Right-align a numeric column so the digits line up. */
  align?: "left" | "right"
}

/** Props for the Loam data table. */
export interface DataTableProps<TRow> {
  columns: DataTableColumn<TRow>[]
  data: TRow[]
  /** Show the pager under the table. */
  pagination?: boolean
  /** Rows per page while paging is on. Defaults to five. */
  pageSize?: number
  caption?: React.ReactNode
  /** Stable row key. Falls back to the row index. */
  getRowId?: (row: TRow, index: number) => string
  /** Shown in place of the rows when the data is empty. */
  emptyMessage?: string
  className?: string
}

type SortState = { id: string; direction: "asc" | "desc" } | null

// Numeric collation puts "9" before "20" before "100"; a plain string
// compare puts "100" first.
const collator = new Intl.Collator(undefined, { numeric: true, sensitivity: "base" })

/** Narrows a cell to a number, so two of them sort by value. */
function isNumberCell<TCell>(cell: TCell | number): cell is number {
  return typeof cell === "number"
}

function compareCells<TCell>(a: TCell, b: TCell) {
  if (isNumberCell(a) && isNumberCell(b)) return a - b
  return collator.compare(String(a ?? ""), String(b ?? ""))
}

/** A sortable, pageable table built from the Loam Table primitives. */
export function DataTable<TRow>({
  columns,
  data,
  pagination = false,
  pageSize = 5,
  caption,
  getRowId,
  emptyMessage = "No rows to show.",
  className,
}: DataTableProps<TRow>) {
  const [sort, setSort] = React.useState<SortState>(null)
  const [page, setPage] = React.useState(0)

  const sorted = React.useMemo(() => {
    if (!sort) return data
    const column = columns.find((item) => item.id === sort.id)
    if (!column?.sortValue) return data
    const read = column.sortValue
    const sign = sort.direction === "asc" ? 1 : -1
    return [...data].sort((left, right) => sign * compareCells(read(left), read(right)))
  }, [columns, data, sort])

  const pageCount = pagination ? Math.max(1, Math.ceil(sorted.length / pageSize)) : 1
  const current = Math.min(page, pageCount - 1)
  const rows = pagination
    ? sorted.slice(current * pageSize, current * pageSize + pageSize)
    : sorted

  function toggleSort(id: string) {
    setPage(0)
    setSort((previous) => {
      if (previous?.id !== id) return { id, direction: "asc" }
      if (previous.direction === "asc") return { id, direction: "desc" }
      return null
    })
  }

  return (
    <div data-slot="data-table" className={cn("flex w-full flex-col gap-3", className)}>
      <Table>
        {caption ? <TableCaption>{caption}</TableCaption> : null}
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            {columns.map((column) => {
              const active = sort?.id === column.id
              return (
                <TableHead
                  key={column.id}
                  className={column.align === "right" ? "text-right" : undefined}
                  aria-sort={
                    active ? (sort?.direction === "asc" ? "ascending" : "descending") : undefined
                  }
                >
                  {column.sortValue ? (
                    <button
                      type="button"
                      onClick={() => toggleSort(column.id)}
                      className={cn(
                        "inline-flex items-center gap-1.5 rounded-[var(--radius-control)] px-2 py-1 -mx-2",
                        "text-xs font-semibold tracking-wide uppercase cursor-pointer",
                        "transition-colors duration-fast hover:bg-accent hover:text-accent-foreground",
                        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/50 focus-visible:ring-offset-2 focus-visible:ring-offset-card",
                        "active:scale-[0.96]",
                        active && "text-foreground"
                      )}
                    >
                      {column.header}
                      {active ? (
                        sort?.direction === "asc" ? (
                          <ArrowUp className="size-3" />
                        ) : (
                          <ArrowDown className="size-3" />
                        )
                      ) : (
                        <ChevronsUpDown className="size-3 opacity-60" />
                      )}
                    </button>
                  ) : (
                    column.header
                  )}
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={columns.length}
                className="py-10 text-center text-sm text-muted-foreground"
              >
                {emptyMessage}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row, index) => (
              <TableRow key={getRowId ? getRowId(row, index) : index}>
                {columns.map((column) => (
                  <TableCell
                    key={column.id}
                    className={column.align === "right" ? "text-right tabular-nums" : undefined}
                  >
                    {column.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {pagination ? (
        <div className="flex items-center justify-between gap-3 px-1">
          <p className="text-xs font-semibold text-muted-foreground">
            Page {current + 1} of {pageCount}
          </p>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              disabled={current === 0}
              onClick={() => setPage(current - 1)}
            >
              <ChevronLeft />
              Previous
            </Button>
            <Button
              variant="outline"
              size="sm"
              disabled={current >= pageCount - 1}
              onClick={() => setPage(current + 1)}
            >
              Next
              <ChevronRight />
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  )
}
