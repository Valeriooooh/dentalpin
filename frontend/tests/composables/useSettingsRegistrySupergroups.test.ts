import { mountSuspended } from '@nuxt/test-utils/runtime'
import { describe, expect, it } from 'vitest'
import { defineComponent, h } from 'vue'

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

function grant(perms: string[]): void {
  const state = useState('auth:permissions', () => [])
  state.value = perms
}

describe('useSettingsRegistry supergroups', () => {
  it('groups every visible category under its canonical supergroup, in rail order', async () => {
    const { supergroups, categories } = await runInSetup(() => {
      grant(['admin.users.read', 'admin.clinic.read'])
      return useSettingsRegistry()
    })
    expect(supergroups.value.map(g => g.id)).toEqual([
      'clinicalSetup',
      'clinicalManagement',
      'financialConfiguration',
      'systemAddons',
      'myPreferences'
    ])
    for (const group of supergroups.value) {
      expect(group.labelKey).toBe(`settings.supergroups.${group.id}.label`)
    }
    // No category is orphaned: every visible category lands in exactly one group.
    const grouped = supergroups.value.flatMap(g => g.categories.map(c => c.id))
    expect(grouped).toEqual(categories.value.map(c => c.id))
    expect(grouped).toHaveLength(9)
  })

  it('drops categories hidden by permissions from their group, keeping the rail totals coherent', async () => {
    const { supergroups, categories } = await runInSetup(() => {
      grant([])
      return useSettingsRegistry()
    })
    const grouped = supergroups.value.flatMap(g => g.categories.map(c => c.id))
    expect(grouped).toEqual(categories.value.map(c => c.id))
    // people (admin.users.read) and modules (admin.clinic.read) are invisible.
    expect(grouped).not.toContain('people')
    expect(grouped).not.toContain('modules')
    // Every group still holds at least one category, so none collapses.
    expect(supergroups.value).toHaveLength(5)
    expect(grouped).toHaveLength(7)
  })
})
