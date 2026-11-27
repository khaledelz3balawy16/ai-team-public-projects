export const statusBadge = (status: string): string => {
  const map: Record<string, string> = {
    'Ready': 'CHANGE_ME',
    'Almost Ready': 'bg-primary-100 text-primary-700',
    'Needs Preparation': 'bg-amber-100 text-amber-700',
    'At Risk': 'bg-red-100 text-red-700',
    'On Track': 'CHANGE_ME',
    'Behind': 'bg-amber-100 text-amber-700',
    'Needs Attention': 'bg-amber-100 text-amber-700',
    'No Concerns': 'CHANGE_ME',
    'Support Requested': 'bg-amber-100 text-amber-700',
    'Wellbeing Check Required': 'bg-red-100 text-red-700',
    'Complete': 'CHANGE_ME',
    'In Progress': 'bg-primary-100 text-primary-700',
    'Overdue': 'bg-red-100 text-red-700',
    'Not Started': 'bg-foreground-100 text-foreground-700',
    'Preparation Required': 'bg-amber-100 text-amber-700',
    'Scheduled': 'bg-primary-100 text-primary-700',
    'Completed': 'CHANGE_ME',
    'Green': 'CHANGE_ME',
    'Amber': 'bg-amber-100 text-amber-700',
    'Red': 'bg-red-100 text-red-700',
  };
  return map[status] || 'bg-background-100 text-foreground-700';
};

export const riskColor = (risk: string): { dot: string; border: string } => {
  const map: Record<string, { dot: string; border: string }> = {
    low: { dot: 'bg-emerald-400', border: 'border-emerald-500/25' },
    medium: { dot: 'bg-amber-400', border: 'border-amber-500/25' },
    high: { dot: 'bg-red-400', border: 'border-red-500/25' },
  };
  return map[risk] || { dot: 'bg-foreground-300', border: 'border-foreground-200' };
};