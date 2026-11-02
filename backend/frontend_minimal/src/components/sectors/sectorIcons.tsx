import { Activity, BrainCircuit, Plane, SquareTerminal, Zap, type LucideIcon } from 'lucide-react';

/** Ícono y color (tokens --color-sector-*) de cada sector del catálogo. */
export const SECTOR_STYLE: Record<string, { icon: LucideIcon; color: string; soft: string }> = {
  technology: { icon: SquareTerminal, color: 'var(--color-sector-tech)', soft: 'var(--color-sector-tech-soft)' },
  energy: { icon: Zap, color: 'var(--color-sector-energy)', soft: 'var(--color-sector-energy-soft)' },
  health: { icon: Activity, color: 'var(--color-sector-health)', soft: 'var(--color-sector-health-soft)' },
  knowledge_economy: { icon: BrainCircuit, color: 'var(--color-sector-knowledge)', soft: 'var(--color-sector-knowledge-soft)' },
  tourism: { icon: Plane, color: 'var(--color-sector-tourism)', soft: 'var(--color-sector-tourism-soft)' },
};
export const DEFAULT_SECTOR_STYLE = SECTOR_STYLE.technology;
