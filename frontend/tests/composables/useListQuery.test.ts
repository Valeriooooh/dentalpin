import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'

interface Filters {
  q: string
  status: string[]
}

const defaults: Filters = { q: '', status: ['active'] }

async function settle(urlReflects: () => void): Promise<void> {
  // The URL push is debounced behind the search key's timer, and the
  // route watcher that re-parses it runs a tick later. Poll for the URL
  // instead of sleeping a fixed time: 400 ms against the 300 ms debounce
  // plus an async router.replace was too tight for slow CI runners.
  await vi.waitFor(urlReflects, { timeout: 5000 })
  await nextTick()
  await nextTick()
}

async function runInSetup<T>(fn: () => T): Promise<T> {
  let captured!: T
  await mountSuspended(defineComponent({
    setup() {
      captured = fn()
      return () => h('div')
    }
  }))
  return captured
}

describe('useListQuery array filters with a non-empty default', () => {
  it('keeps an explicitly cleared array cleared (#473)', async () => {
    const { filters, setFilter } = await runInSetup(() =>
      useListQuery<Filters, { id: string }>({
        defaults,
        pageSize: 20,
        sortable: [],
        defaultSort: '',
        searchKey: 'q',
        fetcher: async () => ({ data: [], total: 0 })
      })
    )
    const route = useRoute()

    // The user picks Archived: the URL records it.
    setFilter('status', ['archived'])
    await settle(() => expect(route.query.status).toBe('archived'))
    expect(filters.value.status).toEqual(['archived'])

    // ...then clears the filter. An empty selection must survive the
    // round trip through the URL; before the fix the key was dropped
    // entirely and re-parsing brought the default back.
    setFilter('status', [])
    await settle(() => expect(route.query.status).toBe(''))
    expect(filters.value.status).toEqual([])
  })

  it('still omits a filter whose default is already empty', async () => {
    const { filters, setFilter } = await runInSetup(() =>
      useListQuery<Filters, { id: string }>({
        defaults,
        pageSize: 20,
        sortable: [],
        defaultSort: '',
        searchKey: 'q',
        fetcher: async () => ({ data: [], total: 0 })
      })
    )
    const route = useRoute()

    setFilter('q', 'ana')
    await settle(() => expect(route.query.q).toBe('ana'))

    // Back to the default: nothing to record, so the key leaves the URL
    // rather than becoming `?q=` noise.
    setFilter('q', '')
    await settle(() => expect(route.query.q).toBeUndefined())
    expect(filters.value.q).toBe('')
  })
})
