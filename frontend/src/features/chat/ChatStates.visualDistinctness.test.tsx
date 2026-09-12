/**
 * Confirms insufficient_data, uncertainty, generic_fallback, and refusal
 * each get real, distinct visual treatment — not just a distinct
 * `data-response-mode` attribute (NormalResponse.test.tsx already covers
 * that plumbing check). Before this test, insufficient_data, uncertainty,
 * and generic_fallback all shared one identical CSS rule (same icon
 * glyph, same colour), so a user would only be able to tell them apart by
 * reading the text carefully — the opposite of what
 * docs/ui/chat-states-design.md's intro line requires ("visually distinct
 * enough that a user should never have to read carefully").
 *
 * FLAGGED FOR SHENG WANG'S REVIEW — this is his role's deliverable
 * (Conversational Interface Lead, Weekly_Plan.md Week 6), implemented
 * here to close a real gap rather than left as a documentation note; not
 * presented as his finished/signed-off work.
 *
 * Reads App.css's raw source from disk via Node's `fs` rather than
 * asserting on jsdom's computed style: Vitest's default config in this
 * project does not enable `test.css`, so a plain CSS import is stubbed
 * out at render time (and, tried here first, so is Vite's usual
 * `?raw` import suffix — this project's Vitest still returns an empty
 * string for a `*.css?raw` import specifically) — reading the actual
 * stylesheet source directly is the reliable way to pin this down here.
 *
 * The `/// <reference types="node" />` below is a deliberate, file-local
 * opt-in: this file is part of the same `src` tree tsconfig.app.json
 * compiles for the browser (which intentionally excludes Node's ambient
 * types, `"types": ["vite/client"]` only), so Node's `fs`/`path` modules
 * aren't visible here by default — a triple-slash reference pulls in
 * @types/node's declarations for just this one file (already an
 * installed devDependency; no new dependency added) without changing
 * that project-wide restriction for every other file under `src`.
 */
/// <reference types="node" />
import { readFileSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

import { describe, expect, it } from 'vitest'

const here = dirname(fileURLToPath(import.meta.url))
const appCss = readFileSync(resolve(here, '../../App.css'), 'utf-8')

// crisis_aware_fallback deliberately reuses the base "i" icon glyph and
// differentiates purely via its full-width, high-contrast colour treatment
// (docs/ui/chat-states-design.md row 6) -- so it's covered by its own
// colour-only test below, not the shared icon-content check.
const RESPONSE_MODE_STATES_WITH_OWN_ICON = [
  'insufficient_data',
  'uncertainty',
  'refusal',
  'generic_fallback',
] as const

function iconContentFor(mode: string): string | null {
  // Matches ".state-card--<mode> .state-card-icon::after { ... content: "X"; ... }"
  const blockPattern = new RegExp(
    `\\.state-card--${mode}\\s+\\.state-card-icon::after\\s*{([^}]*)}`,
    's',
  )
  const block = appCss.match(blockPattern)?.[1]
  if (!block) return null
  return block.match(/content:\s*"([^"]*)"/)?.[1] ?? null
}

function borderLeftColorFor(mode: string): string | null {
  // A mode's border-left-color may be declared on its own selector, or
  // shared via a comma-joined selector list (e.g. refusal + generic_fallback
  // sharing one rule) -- match either.
  const pattern = new RegExp(
    `(?:^|,\\s*)\\.state-card--${mode}(?:\\s*,[^{]*)?\\s*{[^}]*border-left-color:\\s*([^;]+);`,
    'ms',
  )
  return appCss.match(pattern)?.[1]?.trim() ?? null
}

describe('chat state visual distinctness (App.css source)', () => {
  it.each(RESPONSE_MODE_STATES_WITH_OWN_ICON)('defines its own icon for %s', (mode) => {
    expect(iconContentFor(mode)).not.toBeNull()
  })

  it('gives insufficient_data, uncertainty, and generic_fallback three different icons', () => {
    const icons = ['insufficient_data', 'uncertainty', 'generic_fallback'].map(iconContentFor)
    expect(new Set(icons).size).toBe(3)
  })

  it('gives refusal and generic_fallback different icons despite sharing a colour family', () => {
    // docs/ui/chat-states-design.md row 5: generic_fallback is "same
    // visual family as Refusal but with a small icon" -- same colour,
    // must still be a different icon.
    expect(iconContentFor('refusal')).not.toBe(iconContentFor('generic_fallback'))
    expect(borderLeftColorFor('refusal')).toBe(borderLeftColorFor('generic_fallback'))
  })

  it('gives insufficient_data and uncertainty different accent colours within the amber family', () => {
    const insufficientColor = borderLeftColorFor('insufficient_data')
    const uncertaintyColor = borderLeftColorFor('uncertainty')
    expect(insufficientColor).not.toBeNull()
    expect(uncertaintyColor).not.toBeNull()
    expect(insufficientColor).not.toBe(uncertaintyColor)
  })

  it('keeps crisis_aware_fallback the most visually distinct (its own colour, not amber or rose)', () => {
    const crisisBlock = appCss.match(/\.state-card--crisis_aware_fallback\s*{([^}]*)}/s)?.[1]
    expect(crisisBlock).toBeTruthy()
    expect(crisisBlock).toMatch(/background:/)
    // Must not reuse the amber/rose family tokens used by the other states.
    expect(crisisBlock).not.toMatch(/var\(--amber-100\)|var\(--rose-100\)/)
  })
})
