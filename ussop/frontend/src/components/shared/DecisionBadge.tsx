import { Badge } from '@/components/ui/Badge'
export function DecisionBadge({ decision }: { decision: string }) {
  const v = decision === 'pass' ? 'pass' : decision === 'fail' ? 'fail' : 'uncertain'
  return <Badge variant={v}>{decision}</Badge>
}
