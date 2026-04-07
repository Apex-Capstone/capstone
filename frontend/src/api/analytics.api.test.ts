/**
 * Verification tests for analytics.api.ts
 *
 * Covers:
 *   - fetchMySessionAnalytics: HTTP call, DTO→model mapping, empty list, error propagation
 *   - fromDTO: field rename correctness, optional field handling
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import api from '@/api/client'
import { fetchMySessionAnalytics } from '@/api/analytics.api'
import type { TraineeSessionAnalyticsDTO } from '@/types/analytics'

vi.mock('@/api/client', () => ({
  default: {
    get: vi.fn(),
  },
}))

const mockedGet = vi.mocked(api.get)

// ---------------------------------------------------------------------------
// Test data helpers
// ---------------------------------------------------------------------------

function makeDTORow(overrides: Partial<TraineeSessionAnalyticsDTO> = {}): TraineeSessionAnalyticsDTO {
  return {
    session_id: 1,
    case_id: 10,
    case_title: 'Oncology Case',
    empathy_score: 72.0,
    communication_score: 68.0,
    clinical_score: 55.0,
    spikes_completion_score: 50.0,
    spikes_coverage_percent: 67.0,
    duration_seconds: 300,
    created_at: '2024-03-15T10:00:00Z',
    ...overrides,
  }
}

// ---------------------------------------------------------------------------
// fetchMySessionAnalytics
// ---------------------------------------------------------------------------

describe('fetchMySessionAnalytics', () => {
  beforeEach(() => {
    mockedGet.mockReset()
  })

  it('calls GET /v1/analytics/my-sessions', async () => {
    mockedGet.mockResolvedValue({ data: [] })
    await fetchMySessionAnalytics()
    expect(mockedGet).toHaveBeenCalledOnce()
    expect(mockedGet).toHaveBeenCalledWith('/v1/analytics/my-sessions')
  })

  it('returns an empty array when the API returns an empty list', async () => {
    mockedGet.mockResolvedValue({ data: [] })
    const result = await fetchMySessionAnalytics()
    expect(result).toEqual([])
  })

  it('maps session_id to sessionId', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ session_id: 42 })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.sessionId).toBe(42)
  })

  it('maps case_id to caseId', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ case_id: 99 })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.caseId).toBe(99)
  })

  it('maps case_title to caseTitle', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ case_title: 'Cardiology' })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.caseTitle).toBe('Cardiology')
  })

  it('maps all numeric score fields', async () => {
    const dto = makeDTORow({
      empathy_score: 80.5,
      communication_score: 75.0,
      clinical_score: 60.0,
      spikes_completion_score: 55.0,
      spikes_coverage_percent: 83.3,
    })
    mockedGet.mockResolvedValue({ data: [dto] })
    const [row] = await fetchMySessionAnalytics()

    expect(row.empathyScore).toBe(80.5)
    expect(row.communicationScore).toBe(75.0)
    expect(row.clinicalScore).toBe(60.0)
    expect(row.spikesCompletionScore).toBe(55.0)
    expect(row.spikesCoveragePercent).toBe(83.3)
  })

  it('maps duration_seconds to durationSeconds', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ duration_seconds: 180 })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.durationSeconds).toBe(180)
  })

  it('maps created_at to createdAt', async () => {
    mockedGet.mockResolvedValue({
      data: [makeDTORow({ created_at: '2024-06-01T08:30:00Z' })],
    })
    const [row] = await fetchMySessionAnalytics()
    expect(row.createdAt).toBe('2024-06-01T08:30:00Z')
  })

  it('maps numeric overall_score to overallScore', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ overall_score: 67.5 })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.overallScore).toBe(67.5)
  })

  it('omits overallScore when overall_score is null', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ overall_score: null })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.overallScore).toBeUndefined()
  })

  it('omits overallScore when overall_score is absent', async () => {
    const dto = makeDTORow()
    delete (dto as Partial<TraineeSessionAnalyticsDTO>).overall_score
    mockedGet.mockResolvedValue({ data: [dto] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.overallScore).toBeUndefined()
  })

  it('maps numeric eo_addressed_rate to eoAddressedRate', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ eo_addressed_rate: 80.0 })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.eoAddressedRate).toBe(80.0)
  })

  it('omits eoAddressedRate when eo_addressed_rate is null', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ eo_addressed_rate: null })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.eoAddressedRate).toBeUndefined()
  })

  it('maps non-empty spikes_stages_covered to spikesStagesCovered', async () => {
    mockedGet.mockResolvedValue({
      data: [makeDTORow({ spikes_stages_covered: ['S', 'P', 'I'] })],
    })
    const [row] = await fetchMySessionAnalytics()
    expect(row.spikesStagesCovered).toEqual(['S', 'P', 'I'])
  })

  it('omits spikesStagesCovered when spikes_stages_covered is empty array', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ spikes_stages_covered: [] })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.spikesStagesCovered).toBeUndefined()
  })

  it('omits spikesStagesCovered when spikes_stages_covered is null', async () => {
    mockedGet.mockResolvedValue({ data: [makeDTORow({ spikes_stages_covered: null })] })
    const [row] = await fetchMySessionAnalytics()
    expect(row.spikesStagesCovered).toBeUndefined()
  })

  it('converts all stage codes to strings', async () => {
    mockedGet.mockResolvedValue({
      data: [makeDTORow({ spikes_stages_covered: ['S', 'P'] })],
    })
    const [row] = await fetchMySessionAnalytics()
    expect(row.spikesStagesCovered?.every((s) => typeof s === 'string')).toBe(true)
  })

  it('maps multiple sessions correctly', async () => {
    const dtos = [
      makeDTORow({ session_id: 1, empathy_score: 70.0 }),
      makeDTORow({ session_id: 2, empathy_score: 85.0 }),
      makeDTORow({ session_id: 3, empathy_score: 60.0 }),
    ]
    mockedGet.mockResolvedValue({ data: dtos })
    const result = await fetchMySessionAnalytics()

    expect(result).toHaveLength(3)
    expect(result.map((r) => r.sessionId)).toEqual([1, 2, 3])
    expect(result.map((r) => r.empathyScore)).toEqual([70.0, 85.0, 60.0])
  })

  it('propagates API errors to the caller', async () => {
    const error = new Error('Network error')
    mockedGet.mockRejectedValue(error)
    await expect(fetchMySessionAnalytics()).rejects.toThrow('Network error')
  })

  it('propagates 401 errors unchanged', async () => {
    const axiosError = Object.assign(new Error('Unauthorized'), {
      response: { status: 401 },
    })
    mockedGet.mockRejectedValue(axiosError)
    await expect(fetchMySessionAnalytics()).rejects.toMatchObject({
      response: { status: 401 },
    })
  })
})
