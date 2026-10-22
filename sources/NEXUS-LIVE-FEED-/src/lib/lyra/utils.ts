/**
 * AUREON OS - LYRA UTILITIES (v9.0 Unity Edition)
 * Prime Sentinel: GARY LECKEY 02111991
 *
 * Foundational, stateless utility functions that support the Lyra Core.
 * These are the basic mathematical atoms of a harmonious system.
 */

/**
 * Constrains a value to be within a specified range.
 * This is a fundamental function for ensuring stability and preventing
 * chaotic, unbound values within the system's expression.
 *
 * @param value The value to clamp.
 * @param min The lower boundary of the range.
 * @param max The upper boundary of the range.
 * @returns The clamped value.
 */
export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}
