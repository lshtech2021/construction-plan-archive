import { Badge } from './Badge';
import type { ProcessingStatus } from '../../api/types';

interface StatusBadgeProps {
  status: ProcessingStatus;
}

const config: Record<
  ProcessingStatus,
  { label: string; color: 'yellow' | 'blue' | 'green' | 'red' }
> = {
  pending: { label: 'Pending', color: 'yellow' },
  processing: { label: 'Processing', color: 'blue' },
  completed: { label: 'Completed', color: 'green' },
  failed: { label: 'Failed', color: 'red' },
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const { label, color } = config[status] ?? {
    label: status,
    color: 'gray' as const,
  };
  return <Badge color={color}>{label}</Badge>;
}
