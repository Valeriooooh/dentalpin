<script setup lang="ts">
/**
 * PatientSegmentsCard — clinic-local patient tags (grouping only).
 *
 * Registered into `patient.summary.cards` by patient_segments. Chips of
 * the patient's segments with remove, an add-row (existing segments
 * dropdown + inline create), all gated on `patient_segments.write`.
 * Uses the host `SummaryCard` shell like every other summary card.
 */
import type { PatientExtended } from '~~/app/types'
import { PERMISSIONS } from '~~/app/config/permissions'

interface Ctx {
  patient: PatientExtended
}

const props = defineProps<{ ctx: Ctx }>()

const { t } = useI18n()
const { can } = usePermissions()
const canWrite = computed(() => can(PERMISSIONS.patientSegments.write))
const patientId = computed(() => props.ctx.patient.id)
const { segments, allSegments, isLoading, isSaving, fetchAll, createSegment, assignSegment, removeSegment }
  = usePatientSegments(patientId)

onMounted(fetchAll)

const showAdd = ref(false)
const newName = ref('')
// undefined (never '') — USelectMenu's v-model is T | undefined.
const picked = ref<{ label: string, value: string } | undefined>(undefined)

const unassigned = computed(() => {
  const mine = new Set(segments.value.map(s => s.id))
  return allSegments.value
    .filter(s => !mine.has(s.id))
    .map(s => ({ label: s.name, value: s.id }))
})

async function addExisting(opt: { label: string, value: string } | undefined) {
  if (!opt) return
  await assignSegment(opt.value)
  picked.value = undefined
}

async function createAndAssign() {
  const name = newName.value.trim()
  if (!name) return
  const created = await createSegment(name)
  await assignSegment(created.id)
  newName.value = ''
  showAdd.value = false
}
</script>

<template>
  <SummaryCard
    :title="t('patientSegments.title')"
    icon="i-lucide-tags"
    severity="neutral"
    :loading="isLoading"
    :empty="segments.length === 0 && !showAdd"
  >
    <template
      v-if="canWrite"
      #header-trailing
    >
      <UButton
        icon="i-lucide-plus"
        size="xs"
        color="neutral"
        variant="ghost"
        class="ms-auto"
        :aria-label="t('patientSegments.add')"
        @click="showAdd = !showAdd"
      />
    </template>

    <template #empty>
      {{ t('patientSegments.emptyHint') }}
    </template>

    <div class="space-y-2">
      <p
        v-if="segments.length === 0"
        class="text-caption text-muted"
      >
        {{ t('patientSegments.emptyHint') }}
      </p>
      <div
        v-else
        class="flex flex-wrap gap-1.5"
      >
        <UBadge
          v-for="segment in segments"
          :key="segment.id"
          variant="subtle"
          :style="segment.color ? { backgroundColor: segment.color, color: '#fff' } : {}"
        >
          {{ segment.name }}
          <UButton
            v-if="canWrite"
            icon="i-lucide-x"
            size="xs"
            color="neutral"
            variant="ghost"
            :aria-label="t('patientSegments.remove')"
            @click="removeSegment(segment.id)"
          />
        </UBadge>
      </div>

      <div
        v-if="showAdd && canWrite"
        class="space-y-2"
      >
        <USelectMenu
          v-if="unassigned.length > 0"
          v-model="picked"
          size="sm"
          :placeholder="t('patientSegments.pickExisting')"
          :items="unassigned"
          :loading="isSaving"
          @update:model-value="addExisting"
        />
        <div class="flex gap-1.5">
          <UInput
            v-model="newName"
            size="sm"
            :placeholder="t('patientSegments.newName')"
            class="flex-1"
            @keyup.enter="createAndAssign"
          />
          <UButton
            size="sm"
            :disabled="!newName.trim()"
            :loading="isSaving"
            @click="createAndAssign"
          >
            {{ t('patientSegments.create') }}
          </UButton>
        </div>
      </div>
    </div>
  </SummaryCard>
</template>
