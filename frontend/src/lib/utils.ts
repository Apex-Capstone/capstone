import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Merges Tailwind class names and resolves conflicts using `tailwind-merge`.
 *
 * @remarks
 * Combines `clsx` output with `tailwind-merge` so later classes win for conflicting utilities.
 *
 * @param inputs - Class values accepted by `clsx` (strings, objects, arrays, falsy to omit)
 * @returns A single merged class string safe for a `className` prop
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

