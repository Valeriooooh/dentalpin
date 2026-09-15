import { describe, expect, it, vi, beforeEach } from 'vitest'
import { mockNuxtImport } from '@nuxt/test-utils/runtime'

/**
 * #452: the access cookie can expire while the copilot panel sits open.
 * A 401 arrives before any SSE frame is read, so the stream may refresh
 * and retry once; a failed refresh must say so in words rather than
 * dropping "HTTP 401" into the chat.
 */
const refresh = vi.fn(async () => true)
const logout = vi.fn(async () => {})

mockNuxtImport('useAuth', () => () => ({ refresh, logout }))
mockNuxtImport('useI18n', () => () => ({ t: (key: string, fallback?: string) => fallback ?? key }))

function sseResponse(body: string): Response {
  return new Response(body, { status: 200, headers: { 'Content-Type': 'text/event-stream' } })
}

async function runStream() {
  const { useCopilotStream } = await import(
    '#module-layers/copilot/frontend/composables/useCopilotStream'
  )
  const events: [string, Record<string, unknown>][] = []
  const errors: string[] = []
  await useCopilotStream().stream('/api/v1/copilot/chat', { text: 'hi' }, {
    onEvent: (event, data) => events.push([event, data]),
    onError: message => errors.push(message)
  })
  return { events, errors }
}

describe('useCopilotStream authentication', () => {
  beforeEach(() => {
    refresh.mockClear()
    refresh.mockResolvedValue(true)
    logout.mockClear()
  })

  it('streams without refreshing while the session is valid', async () => {
    const fetchMock = vi.fn(async () => sseResponse('event: token\ndata: {"text":"hi"}\n\n'))
    vi.stubGlobal('fetch', fetchMock)

    const { events, errors } = await runStream()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(refresh).not.toHaveBeenCalled()
    expect(events).toEqual([['token', { text: 'hi' }]])
    expect(errors).toEqual([])
  })

  it('refreshes once and replays the turn when the access cookie has expired', async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce(new Response('', { status: 401 }))
      .mockResolvedValueOnce(sseResponse('event: token\ndata: {"text":"back"}\n\n'))
    vi.stubGlobal('fetch', fetchMock)

    const { events, errors } = await runStream()

    expect(refresh).toHaveBeenCalledTimes(1)
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(events).toEqual([['token', { text: 'back' }]])
    expect(errors).toEqual([])
    expect(logout).not.toHaveBeenCalled()
  })

  it('says the session expired, in words, when the refresh fails', async () => {
    refresh.mockResolvedValue(false)
    const fetchMock = vi.fn(async () => new Response('', { status: 401 }))
    vi.stubGlobal('fetch', fetchMock)

    const { events, errors } = await runStream()

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(logout).toHaveBeenCalledTimes(1)
    expect(events).toEqual([])
    expect(errors).toEqual(['Your session has expired. Sign in again to continue.'])
  })
})
