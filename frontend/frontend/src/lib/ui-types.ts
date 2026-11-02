/** Tipos de presentación compartidos por las tablas y listados de la UI. */

export type RankingItem = {
  rank: number;
  title: string;
  meta: string;
  score: number | null;
  delta?: string;
  badge?: string;
  note?: string;
};

export type OccupationRow = {
  rank: number;
  name: string;
  family: string;
  ciuo: string;
  country: string;
  score: number;
  demand: string;
  salary: string;
  insertion: string;
  risk: string;
  riskLabel: string;
  coverage: number;
};

export type GapRow = {
  skill: string;
  country: string;
  demand: string;
  training: string;
  gap: number;
  occupations: number;
  mainOccupations: string;
};

export type TrendFeedItem = {
  id?: string;
  title: string;
  detail: string;
  date: string;
  country: string;
};

export type QuickAccess = {
  title: string;
  description: string;
  href: string;
  icon: 'globe' | 'layers' | 'briefcase' | 'graduation' | 'trend';
  featured?: boolean;
};
