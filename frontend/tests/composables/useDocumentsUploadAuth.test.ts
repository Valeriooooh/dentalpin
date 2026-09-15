import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'

/**
 * #452: the document upload stays on `$fetch` because it carries FormData
 * and reports progress, so it needs its own 401 recovery — the same one
 * refresh, one retry contract `useApi` gives everything else.
 */
const refresh = vi.fn(async () => true)

mockNuxtImport('useAuth', () => () => ({ refresh, logout: vi.fn() }))
mockNuxtImport('useI18n', () => () => ({ t: (key: string, fallback?: string) => fallback ?? key }))
mockNuxtImport('useToast', () => () => ({ add: vi.fn() }))
mockNuxtImport('useApi', () => () => ({
  get: vi.fn(), post: vi.fn(), put: vi.fn(), patch: vi.fn(), del: vi.fn(), raw: vi.fn()
}))

async function upload() {
  const { useDocuments } = await import('#module-layers/media/frontend/composables/useDocuments')
  const file = new File(['x'], 'xray.png', { type: 'image/png' })
  return await useDocuments().uploadDocument('patient-1', file, 'xray', 'Panoramic')
}

describe('useDocuments().uploadDocument', () => {
  beforeEach(() => {
    refresh.mockClear()
    refresh.mockResolvedValue(true)
  })

  it('uploads once while the session is valid', async () => {
    const fetchMock = vi.fn(async () => ({ data: { id: 'doc-1' } }))
    vi.stubGlobal('$fetch', fetchMock)

    const doc = await upload()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(refresh).not.toHaveBeenCalled()
    expect(doc).toEqual({ id: 'doc-1' })
  })

  it('refreshes once and retries when the access cookie has expired', async () => {
    const fetchMock = vi.fn()
      .mockRejectedValueOnce(Object.assign(new Error('Unauthorized'), { statusCode: 401 }))
      .mockResolvedValueOnce({ data: { id: 'doc-2' } })
    vi.stubGlobal('$fetch', fetchMock)

    const doc = await upload()

    expect(refresh).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(doc).toEqual({ id: 'doc-2' })
  })

  it('gives up when the refresh fails, without a second attempt', async () => {
    refresh.mockResolvedValue(false)
    const fetchMock = vi.fn(async () => {
      throw Object.assign(new Error('Unauthorized'), { statusCode: 401 })
    })
    vi.stubGlobal('$fetch', fetchMock)

    const doc = await upload()

    expect(refresh).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(doc).toBeNull()
  })
})
