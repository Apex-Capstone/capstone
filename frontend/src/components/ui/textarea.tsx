"use client"

/**
 * Multi-line text area with shared focus styles.
 */
import * as React from "react"
import { cn } from "@/lib/utils"

/** Props for {@link Textarea}. */
export interface TextareaProps
  extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

/**
 * Styled `textarea` for forms and long-form input.
 *
 * @param props - {@link TextareaProps}
 * @param ref - Forwarded to the `textarea` element
 * @returns Textarea element
 */
const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={cn(
          "flex min-h-[80px] w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm ring-offset-background placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-apex-500 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        {...props}
      />
    )
  }
)
Textarea.displayName = "Textarea"

export { Textarea }
