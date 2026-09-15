import type { ApiResponse } from '~~/app/types'

export interface PatientSegment {
  id: string
  name: string
  color: string | null
  description: string | null
  member_count: number
  created_at: string
}

export function usePatientSegments(patientId: Ref<string> | ComputedRef<string>) {
  const api = useApi()

  const segments = useState<PatientSegment[]>(`segments:patient:${patientId.value}`, () => [])
  const allSegments = useState<PatientSegment[]>('segments:all', () => [])
  const isLoading = ref(false)
  const isSaving = ref(false)

  async function fetchAll() {
    isLoading.value = true
    try {
      const mine = await api.get<ApiResponse<PatientSegment[]>>(
        `/api/v1/patient_segments/patients/${patientId.value}/segments`
      )
      segments.value = mine.data
      const all = await api.get<ApiResponse<PatientSegment[]>>('/api/v1/patient_segments/segments')
      allSegments.value = all.data
    } finally {
      isLoading.value = false
    }
  }

  async function createSegment(name: string): Promise<PatientSegment> {
    isSaving.value = true
    try {
      const res = await api.post<ApiResponse<PatientSegment>>('/api/v1/patient_segments/segments', { name })
      allSegments.value = [...allSegments.value, res.data]
      return res.data
    } finally {
      isSaving.value = false
    }
  }

  async function assignSegment(segmentId: string) {
    isSaving.value = true
    try {
      const res = await api.post<ApiResponse<PatientSegment[]>>(
        `/api/v1/patient_segments/patients/${patientId.value}/segments`,
        { segment_id: segmentId }
      )
      segments.value = res.data
    } finally {
      isSaving.value = false
    }
  }

  async function removeSegment(segmentId: string) {
    isSaving.value = true
    try {
      await api.del(`/api/v1/patient_segments/patients/${patientId.value}/segments/${segmentId}`)
      segments.value = segments.value.filter(s => s.id !== segmentId)
    } finally {
      isSaving.value = false
    }
  }

  return { segments, allSegments, isLoading, isSaving, fetchAll, createSegment, assignSegment, removeSegment }
}
