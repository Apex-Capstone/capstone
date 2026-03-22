/**
 * Single-line text input with shared focus ring styles.
 */
import * as React from "react"

import { cn } from "@/lib/utils"

/** Props for {@link Input} (standard HTML input attributes). */
export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {}

/**
 * Accessible text input with theme-aligned borders and focus ring.
 *
 * @param props - {@link InputProps}
 * @param ref - Forwarded to the `input` element
 * @returns Input element
 */
const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          "flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm ring-offset-background file:border-0 file:bg-transparent file:text-sm file:font-medium placeholder:text-muted-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50",
          className
        )}
        ref={ref}
        {...props}
      />
    )
  }
)
Input.displayName = "Input"

export { Input }

