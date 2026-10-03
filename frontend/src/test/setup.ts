// Vitest global setup: extends `expect` with jest-dom's DOM matchers
// (toBeInTheDocument, toHaveTextContent, etc.) for every test file, and
// cleans up the DOM between tests so components rendered in one test
// don't leak into the next.
import '@testing-library/jest-dom/vitest'

import { cleanup } from '@testing-library/react'
import { afterEach } from 'vitest'

afterEach(() => {
  cleanup()
})
