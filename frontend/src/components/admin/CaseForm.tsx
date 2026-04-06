/**
 * Admin modal form to create or edit a {@link Case} with plugin pickers.
 */
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchAdminPluginRegistry, fetchAdminPlugins } from '@/api/admin.api'
import type { Case } from '@/types/case'
import type { PluginsResponse, PluginInfo } from '@/types/plugins'

const EVALUATOR_DEFAULT = ''
const PATIENT_MODEL_DEFAULT = ''

/** Fresh form state (no merge with prior row — avoids stale plugin fields). */
function defaultCaseFormValues(): Partial<Case> {
  return {
    title: '',
    script: '',
    description: '',
    objectives: '',
    difficultyLevel: 'intermediate',
    category: '',
    patientBackground: '',
    expectedSpikesFlow: '',
    evaluatorPlugin: null,
    patientModelPlugin: null,
    metricsPlugins: [],
  }
}

/** Props for {@link CaseForm}. */
type Props = {
  open: boolean
  onClose: () => void
  mode: 'create' | 'edit'
  initial?: Partial<Case>
  onSubmit: (values: Partial<Case>) => Promise<void> | void
  submitting?: boolean
}

/**
 * Builds a short label for plugin `<option>` rows (name + optional version).
 *
 * @param p - Plugin metadata from the registry
 * @returns Display string
 */
function pluginLabel(p: PluginInfo) {
  const shortName = p.name.includes(':') ? p.name.split(':').pop() ?? p.name : p.name
  return p.version ? `${shortName} (v${p.version})` : shortName
}

/** Active system-level plugin paths from the admin /plugins endpoint. */
type ActivePluginConfig = { patient_model: string; evaluator: string; metrics: string[] }

/**
 * Matches an active plugin module path (e.g. "plugins.evaluators.apex_hybrid_evaluator:ApexHybridEvaluator")
 * against the registry to produce a human-readable label with version.
 */
function resolveActivePluginLabel(path: string | undefined, registry: PluginInfo[]): string | null {
  if (!path) return null
  for (const p of registry) {
    if (path.includes(p.name) || p.name.includes(path)) return pluginLabel(p)
  }
  if (path.includes(':')) return path.split(':').pop() ?? path
  return path
}

/**
 * Large dialog with sections for metadata, patient, script, and AI plugin overrides.
 *
 * @remarks
 * Loads {@link fetchAdminPluginRegistry} when opened. Clears empty plugin fields before submit.
 *
 * @param props - Open state, mode, optional `initial` case, and `onSubmit` handler
 * @returns Dialog + form JSX
 */
export const CaseForm = ({ open, onClose, mode, initial, onSubmit, submitting }: Props) => {
  const [values, setValues] = useState<Partial<Case>>(defaultCaseFormValues)
  const [plugins, setPlugins] = useState<PluginsResponse | null>(null)
  const [pluginsLoading, setPluginsLoading] = useState(false)
  const [activeConfig, setActiveConfig] = useState<ActivePluginConfig | null>(null)

  // Reset when the dialog opens so plugin fields never inherit a previous case/edit session.
  useEffect(() => {
    if (!open) return
    if (mode === 'edit' && initial) {
      const ev = initial.evaluatorPlugin
      const pm = initial.patientModelPlugin
      setValues({
        ...defaultCaseFormValues(),
        ...initial,
        evaluatorPlugin: ev != null && ev !== '' ? ev : null,
        patientModelPlugin: pm != null && pm !== '' ? pm : null,
        metricsPlugins: Array.isArray(initial.metricsPlugins) ? [...initial.metricsPlugins] : [],
      })
    } else if (mode === 'create') {
      setValues(defaultCaseFormValues())
    }
  }, [open, mode, initial])

  useEffect(() => {
    if (!open) return
    setPluginsLoading(true)
    Promise.all([
      fetchAdminPluginRegistry(),
      fetchAdminPlugins().catch(() => null),
    ])
      .then(([registry, active]) => {
        setPlugins(registry)
        if (active) setActiveConfig(active as unknown as ActivePluginConfig)
      })
      .catch(() => setPlugins(null))
      .finally(() => setPluginsLoading(false))
  }, [open])

  /**
   * Updates a single key in the controlled `values` state.
   *
   * @param k - Case field name
   * @param v - New value
   */
  const set = (k: keyof Case, v: unknown) => setValues((prev) => ({ ...prev, [k]: v }))

  /**
   * Strips placeholder plugin values and invokes the parent `onSubmit` handler.
   *
   * @param e - Form submit event
   */
  const submit = async (e: FormEvent) => {
    e.preventDefault()
    const toSend = { ...values }
    // Use null (not undefined) so PATCH includes the key and the API clears DB columns.
    if (!toSend.evaluatorPlugin || toSend.evaluatorPlugin === EVALUATOR_DEFAULT) {
      toSend.evaluatorPlugin = null
    }
    if (!toSend.patientModelPlugin || toSend.patientModelPlugin === PATIENT_MODEL_DEFAULT) {
      toSend.patientModelPlugin = null
    }
    if (!toSend.metricsPlugins?.length) {
      toSend.metricsPlugins = null
    }
    await onSubmit(toSend)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => (!submitting && !o ? onClose() : undefined)}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'Create Case' : 'Edit Case'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-6">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Section 1 — Case Metadata */}
            <Card className="bg-white shadow rounded-lg">
              <CardHeader>
                <CardTitle className="text-lg">Case Metadata</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Title</label>
                  <Input
                    className="mt-1"
                    value={values.title ?? ''}
                    onChange={(e) => set('title', e.target.value)}
                    required
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Description</label>
                  <Textarea
                    className="mt-1"
                    rows={3}
                    value={values.description ?? ''}
                    onChange={(e) => set('description', e.target.value)}
                  />
                </div>
                <div className="grid gap-4 md:grid-cols-2">
                  <div>
                    <label className="text-sm font-medium">Difficulty</label>
                    <select
                      className="mt-1 w-full border rounded-md h-10 px-3 text-sm"
                      value={values.difficultyLevel ?? 'intermediate'}
                      onChange={(e) => set('difficultyLevel', e.target.value)}
                    >
                      <option value="beginner">beginner</option>
                      <option value="intermediate">intermediate</option>
                      <option value="advanced">advanced</option>
                    </select>
                  </div>
                  <div>
                    <label className="text-sm font-medium">Category</label>
                    <Input
                      className="mt-1"
                      value={values.category ?? ''}
                      onChange={(e) => set('category', e.target.value)}
                    />
                  </div>
                </div>
                <div>
                  <label className="text-sm font-medium">Learning Objectives</label>
                  <Textarea
                    className="mt-1"
                    rows={2}
                    value={values.objectives ?? ''}
                    onChange={(e) => set('objectives', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 2 — Patient Configuration */}
            <Card className="bg-white shadow rounded-lg">
              <CardHeader>
                <CardTitle className="text-lg">Patient Configuration</CardTitle>
              </CardHeader>
              <CardContent>
                <div>
                  <label className="text-sm font-medium">Patient Background</label>
                  <Textarea
                    className="mt-1"
                    rows={2}
                    value={values.patientBackground ?? ''}
                    onChange={(e) => set('patientBackground', e.target.value)}
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 3 — Dialogue Guidance */}
            <Card className="bg-white shadow rounded-lg">
              <CardHeader>
                <CardTitle className="text-lg">Dialogue Guidance</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div>
                  <label className="text-sm font-medium">Expected SPIKES stages</label>
                  <Textarea
                    className="mt-1"
                    rows={2}
                    value={values.expectedSpikesFlow ?? ''}
                    onChange={(e) => set('expectedSpikesFlow', e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-sm font-medium">Case Instructions / Script</label>
                  <Textarea
                    className="mt-1"
                    rows={6}
                    value={values.script ?? ''}
                    onChange={(e) => set('script', e.target.value)}
                    required
                  />
                </div>
              </CardContent>
            </Card>

            {/* Section 4 — AI Configuration */}
            <Card className="bg-white shadow rounded-lg">
              <CardHeader>
                <CardTitle className="text-lg">AI Configuration</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Patient Model</label>
                  <select
                    className="w-full border rounded-md h-10 px-3 text-sm"
                    value={values.patientModelPlugin ?? PATIENT_MODEL_DEFAULT}
                    onChange={(e) =>
                      set('patientModelPlugin', e.target.value ? e.target.value : null)
                    }
                    disabled={pluginsLoading}
                  >
                    <option value={PATIENT_MODEL_DEFAULT}>System Default</option>
                    {plugins?.patient_models.map((model) => (
                      <option key={model.name} value={model.name}>
                        {pluginLabel(model)}
                      </option>
                    ))}
                  </select>
                  {(!values.patientModelPlugin || values.patientModelPlugin === PATIENT_MODEL_DEFAULT) && (
                    <p className="text-xs text-muted-foreground">
                      Currently resolves to{' '}
                      <span className="font-medium text-gray-700">
                        {resolveActivePluginLabel(activeConfig?.patient_model, plugins?.patient_models ?? [])
                          ?? 'DefaultLLMPatientModel (v1.0)'}
                      </span>
                    </p>
                  )}
                </div>

                <div className="space-y-2">
                  <label className="text-sm font-medium">Evaluator Plugin</label>
                  <select
                    className="w-full border rounded-md h-10 px-3 text-sm"
                    value={values.evaluatorPlugin ?? EVALUATOR_DEFAULT}
                    onChange={(e) =>
                      set('evaluatorPlugin', e.target.value ? e.target.value : null)
                    }
                    disabled={pluginsLoading}
                  >
                    <option value={EVALUATOR_DEFAULT}>Default (use system default evaluator)</option>
                    {plugins?.evaluators.map((p) => (
                      <option key={p.name} value={p.name}>
                        {pluginLabel(p)}
                      </option>
                    ))}
                  </select>
                  {(!values.evaluatorPlugin || values.evaluatorPlugin === EVALUATOR_DEFAULT) ? (
                    <p className="text-xs text-muted-foreground">
                      Currently resolves to{' '}
                      <span className="font-medium text-gray-700">
                        {resolveActivePluginLabel(activeConfig?.evaluator, plugins?.evaluators ?? [])
                          ?? 'ApexHybridEvaluator (v1.0)'}
                      </span>
                    </p>
                  ) : (
                    <p className="text-xs text-muted-foreground">
                      Overrides the system default evaluator for this case.
                    </p>
                  )}
                </div>

                <div className="space-y-2 mt-4">
                  <label className="text-sm font-medium">Metrics Plugins</label>
                  <div className="space-y-2">
                    {plugins?.metrics.map((metric) => (
                      <label key={metric.name} className="flex items-center gap-2">
                        <input
                          type="checkbox"
                          checked={values.metricsPlugins?.includes(metric.name) ?? false}
                          onChange={(e) => {
                            const current = values.metricsPlugins ?? []
                            if (e.target.checked) {
                              set('metricsPlugins', [...current, metric.name])
                            } else {
                              set('metricsPlugins', current.filter((m) => m !== metric.name))
                            }
                          }}
                          disabled={pluginsLoading}
                        />
                        {pluginLabel(metric)}
                      </label>
                    ))}
                  </div>
                  {(!plugins?.metrics || plugins.metrics.length === 0) && !pluginsLoading && (
                    <p className="text-xs text-gray-500">No metrics plugins registered.</p>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button type="submit" disabled={submitting}>
              {mode === 'create' ? 'Create' : 'Save changes'}
            </Button>
          </div>
        </form>
      </DialogContent>
    </Dialog>
  )
}
