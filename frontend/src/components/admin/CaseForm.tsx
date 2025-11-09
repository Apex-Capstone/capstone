import { useEffect, useState } from 'react'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import type { Case } from '@/types/case'

type Props = {
  open: boolean
  onClose: () => void
  mode: 'create' | 'edit'
  initial?: Partial<Case>
  onSubmit: (values: Partial<Case>) => Promise<void> | void
  submitting?: boolean
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
  })

  useEffect(() => {
    if (initial) setValues(v => ({ ...v, ...initial }))
  }, [initial])

  const set = (k: keyof Case, v: any) => setValues(prev => ({ ...prev, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    await onSubmit(values)
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !submitting && !o ? onClose() : undefined}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>{mode === 'create' ? 'Create Case' : 'Edit Case'}</DialogTitle>
        </DialogHeader>

        <form onSubmit={submit} className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="md:col-span-2">
              <label className="text-sm font-medium">Title</label>
              <Input
                value={values.title ?? ''}
                onChange={(e) => set('title', e.target.value)}
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium">Script</label>
              <Textarea
                rows={6}
                value={values.script ?? ''}
                onChange={(e) => set('script', e.target.value)}
                required
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium">Description</label>
              <Textarea
                rows={3}
                value={values.description ?? ''}
                onChange={(e) => set('description', e.target.value)}
              />
            </div>

            <div>
              <label className="text-sm font-medium">Difficulty</label>
              <select
                className="w-full border rounded h-10 px-3 text-sm"
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
                value={values.category ?? ''}
                onChange={(e) => set('category', e.target.value)}
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium">Objectives</label>
              <Textarea
                rows={2}
                value={values.objectives ?? ''}
                onChange={(e) => set('objectives', e.target.value)}
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium">Patient Background</label>
              <Textarea
                rows={2}
                value={values.patientBackground ?? ''}
                onChange={(e) => set('patientBackground', e.target.value)}
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-sm font-medium">Expected SPIKES Flow</label>
              <Textarea
                rows={2}
                value={values.expectedSpikesFlow ?? ''}
                onChange={(e) => set('expectedSpikesFlow', e.target.value)}
              />
            </div>
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
