import { Button } from '@/components/ui/button'
import { Pencil, Trash2 } from 'lucide-react'
import type { Case } from '@/types/case'

type Props = {
  items: Case[]
  onEdit: (c: Case) => void
  onDelete: (id: number) => void
}

export const CasesTable = ({ items, onEdit, onDelete }: Props) => {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b">
            <th className="text-left py-2">Title</th>
            <th className="text-left py-2">Difficulty</th>
            <th className="text-left py-2">Category</th>
            <th className="text-left py-2">Updated</th>
            <th className="text-right py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {items.map((c) => (
            <tr key={c.id} className="border-b">
              <td className="py-2">{c.title}</td>
              <td className="py-2">{c.difficultyLevel ?? '—'}</td>
              <td className="py-2">{c.category ?? '—'}</td>
              <td className="py-2">{new Date(c.updatedAt).toLocaleString()}</td>
              <td className="py-2">
                <div className="flex justify-end gap-2">
                  <Button size="sm" variant="outline" onClick={() => onEdit(c)}>
                    <Pencil className="h-4 w-4 mr-1" /> Edit
                  </Button>
                  <Button size="sm" variant="destructive" onClick={() => onDelete(c.id)}>
                    <Trash2 className="h-4 w-4 mr-1" /> Delete
                  </Button>
                </div>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={5} className="py-6 text-center text-gray-500">
                No cases yet.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
