"use client"

import * as React from "react"

import { cn } from "@/lib/utils"
import { Avatar, AvatarFallback, AvatarImage } from "./avatar"

/*
 * Loam AvatarGroup: overlapping circles, so it stays on the control radius.
 *
 * Each circle carries a ring in the page colour, which is what separates one
 * face from the next without adding a shadow. The overflow count is the same
 * circle with the muted paper fill.
 */

/** One member of an avatar group: a photo with initials behind it. */
export interface AvatarGroupMember {
  /** Photo URL. Leave it out to show the initials only. */
  src?: string
  /** Accessible name, also used for the image alt text. */
  name: string
  /** Initials for the fallback. Derived from the name when absent. */
  initials?: string
}

/** Props for the overlapping avatar row. */
export interface AvatarGroupProps extends React.ComponentProps<"div"> {
  /** Render the row from data instead of passing AvatarGroupItem children. */
  members?: AvatarGroupMember[]
  /** How many circles to show before the overflow count. */
  max?: number
}

function initialsFor(member: AvatarGroupMember) {
  if (member.initials) return member.initials
  return member.name
    .split(" ")
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("")
}

/** One circle inside a group, ringed in the page colour so it reads as separate. */
function AvatarGroupItem({
  className,
  ...props
}: React.ComponentProps<typeof Avatar>) {
  return (
    <Avatar
      data-slot="avatar-group-item"
      className={cn("ring-2 ring-background", className)}
      {...props}
    />
  )
}

/** A row of overlapping circles with an optional overflow count at the end. */
function AvatarGroup({
  className,
  members,
  max = 4,
  children,
  ...props
}: AvatarGroupProps) {
  const shown = members ? members.slice(0, max) : []
  const overflow = members ? members.length - shown.length : 0

  return (
    <div
      data-slot="avatar-group"
      className={cn("flex items-center -space-x-2", className)}
      {...props}
    >
      {members
        ? shown.map((member) => (
            <AvatarGroupItem key={member.name} title={member.name}>
              {member.src ? <AvatarImage src={member.src} alt={member.name} /> : null}
              <AvatarFallback>{initialsFor(member)}</AvatarFallback>
            </AvatarGroupItem>
          ))
        : children}
      {overflow > 0 ? (
        <span
          data-slot="avatar-group-overflow"
          className={cn(
            "relative flex size-9 shrink-0 items-center justify-center",
            "rounded-[var(--radius-control)] border border-border bg-muted ring-2 ring-background",
            "text-xs font-semibold text-muted-foreground select-none"
          )}
        >
          +{overflow}
        </span>
      ) : null}
    </div>
  )
}

export { AvatarGroup, AvatarGroupItem }
