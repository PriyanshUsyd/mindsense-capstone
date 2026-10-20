import { render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { getModelCatalog } from '../../api/client'
import { NormalResponse } from './NormalResponse'

vi.mock('../../api/client', async () => {
  const actual = await vi.importActual<typeof import('../../api/client')>('../../api/client')
  return { ...actual, getModelCatalog: vi.fn(), respond: vi.fn() }
})

const mockedGetModelCatalog = vi.mocked(getModelCatalog)

const CATALOG = {
  runtime: 'ollama',
  selection_enabled: true,
  default_model_tag: 'phi4-mini:3.8b',
  available_model_tags: ['phi4-mini:3.8b'],
}

afterEach(() => {
  vi.clearAllMocks()
})

describe('synthetic dataset banner', () => {
  it('shows the demo banner when the backend reports synthetic data', async () => {
    mockedGetModelCatalog.mockResolvedValue({ ...CATALOG, dataset: 'synthetic' })
    render(<NormalResponse />)

    expect(await screen.findByTestId('dataset-banner')).toHaveTextContent(
      'Demo mode: synthetic data',
    )
  })

  it('shows no banner for the real dataset', async () => {
    mockedGetModelCatalog.mockResolvedValue({ ...CATALOG, dataset: 'real' })
    render(<NormalResponse />)

    await screen.findByRole('combobox')
    expect(screen.queryByTestId('dataset-banner')).not.toBeInTheDocument()
  })

  it('shows no banner when the catalog is unavailable', async () => {
    mockedGetModelCatalog.mockRejectedValue(new Error('no catalog'))
    render(<NormalResponse />)

    await screen.findByRole('heading', { level: 1 })
    expect(screen.queryByTestId('dataset-banner')).not.toBeInTheDocument()
  })
})
