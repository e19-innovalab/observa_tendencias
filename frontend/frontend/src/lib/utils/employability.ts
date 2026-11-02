import type { EmployabilityComponent, EmployabilityItem } from '../schemas/api';
import type { OccupationRow } from '../ui-types';
import { formatIndex01, formatNumber, formatSignedPercent, formatUsd, riskLabel } from './format';

export function findComponent(
  item: EmployabilityItem,
  dimension: string,
): EmployabilityComponent | undefined {
  return item.components.find((component) => component.dimension === dimension);
}

/** Fila de la tabla de ranking a partir de un registro real de empleabilidad. */
export function toOccupationRow(item: EmployabilityItem, rank: number): OccupationRow {
  const demand = findComponent(item, 'net_demand');
  const salary = findComponent(item, 'salary_ppp');
  const insertion = findComponent(item, 'insertion_rate');
  const risk = findComponent(item, 'automation_risk');

  return {
    rank,
    name: item.occupation.name,
    family: item.sector_name ?? 'Sin sector',
    ciuo: item.occupation.occupation_code,
    country: item.country_iso3,
    score: item.score ?? 0,
    demand: demand?.raw === null || demand?.raw === undefined ? '—' : formatSignedPercent(demand.raw),
    salary: salary?.raw === null || salary?.raw === undefined ? '—' : formatUsd(salary.raw),
    insertion:
      insertion?.raw === null || insertion?.raw === undefined
        ? '—'
        : `${formatNumber(insertion.raw * 100, 1)}%`,
    risk: risk?.raw === null || risk?.raw === undefined ? '—' : formatIndex01(risk.raw),
    riskLabel: riskLabel(risk?.raw ?? null),
    coverage: Math.round(item.coverage_ratio * 100),
  };
}
