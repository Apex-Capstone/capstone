import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { fetchAdminPluginRegistry, type PluginInfo } from '@/api/admin.api'
import type { Case } from '@/types/case'

const EVALUATOR_DEFAULT = ''

type Props = {
  open: boolean
  onClose: () => void
  mode: 'create' | 'edit'
  initial?: Partial<Case>
  onSubmit: (values: Partial<Case>) => Promise<void> | void
  submitting?: boolean
}

function evaluatorLabel(p: PluginInfo) {
  const shortName = p.name.includes(':') ? p.name.split(':').pop() ?? p.name : p.name
  return p.version ? `${shortName} (v${p.version})` : shortName
}

export const CaseForm = ({ open, onClose, mode, initial, onSubmit, submitting }: Props) => {
  const [values, setValues] = useState<Partial<Case>>({
    title: '',
    script: '',
    description: '',
    objectives: '',
    difficultyLevel: 'intermediate',
    category: '',
    patientBackground: '',
    expectedSpikesFlow: '',
    evaluatorPlugin: '',
  })
  const [evaluators, setEvaluators] = useState<PluginInfo[]>([])
  const [evaluatorsLoading, setEvaluatorsLoading] = useState(false)

  useEffect(() => {
    if (initial) setValues((v) => ({ ...v, ...initial }))
  }, [initial])

  useEffect(() => {
    if (!open) return
    setEvaluatorsLoading(true)
    fetchAdminPluginRegistry()
      .then((r) => setEvaluators(r.evaluators ?? []))
      .catch(() => setEvaluators([]))
      .finally(() => setEvaluatorsLoading(false))
  }, [open])

  const set = (k: keyof Case, v: unknown) => setValues((prev) => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    const toSend = { ...values }
    if (toSend.evaluatorPlugin === EVALUATOR_DEFAULT || toSend.evaluatorPlugin === '') {
      toSend.evaluatorPlugin = undefined
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
              <CardContent>
                <div>
                  <label className="text-sm font-medium">Evaluator Plugin</label>
                  <select
                    className="mt-1 w-full border rounded-md h-10 px-3 text-sm"
                    value={values.evaluatorPlugin ?? EVALUATOR_DEFAULT}
                    onChange={(e) => set('evaluatorPlugin', e.target.value || undefined)}
                    disabled={evaluatorsLoading}
                  >
                    <option value={EVALUATOR_DEFAULT}>Default (use system default evaluator)</option>
                    {evaluators.map((p) => (
                      <option key={p.name} value={p.name}>
                        {evaluatorLabel(p)}
                      </option>
                    ))}
                  </select>
                  <p className="mt-1 text-xs text-gray-500">
                    Override the evaluator for this case. Default uses the system-configured evaluator.
                  </p>
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
