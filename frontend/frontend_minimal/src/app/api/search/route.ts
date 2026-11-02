import { z } from 'zod';
import { SECTIONS } from '@/components/minimal/nav';
import { apiGet } from '@/lib/api/client';
import { getCountries, getSectors } from '@/lib/api/common';
import { getIndicators } from '@/lib/api/panorama';
import { fold, matchScore, tokens } from '@/lib/utils/search';

const OccupationsSchema = z.array(z.object({ occupation_code: z.string(), name: z.string() }).loose());
const SkillsSchema = z.array(z.object({ skill_code: z.string(), name: z.string() }).loose());
/** Resultados por grupo y candidatos que se piden al backend antes de ordenar. */
const MAX = 6;
const CANDIDATES = 30;
const MIN_CHARS = 2;
/** "ciuo 2221" o "2221": código CIUO-08 (1 a 4 dígitos). */
const CODE_WORDS = new Set(['ciuo', 'isco', 'codigo']);
const CODE = /^\d{1,4}$/;
const EXACT = 4;
const GROUP_ORDER = ['Indicadores', 'Sectores', 'Ocupaciones', 'Habilidades', 'Secciones'];
const EXTRA_SECTIONS = [
  { href: '/alertas', label: 'Alertas' },
  { href: '/metodologia/ise', label: 'Metodología' },
];

type Item = { label: string; detail?: string; href: string; score: number };
type Group = { label: string; items: Item[] };

const ranked = (items: Item[]) =>
  items.filter((i) => i.score > 0).sort((a, b) => b.score - a.score || a.label.length - b.label.length).slice(0, MAX);

/**
 * Buscador del encabezado. Entiende la consulta antes de buscar: un número es un código CIUO, el
 * nombre o código de un país se aplica como filtro y el resto son palabras que tienen que aparecer
 * (en cualquier orden, sin tildes) en secciones, sectores, indicadores, ocupaciones y habilidades.
 */
export async function GET(request: Request) {
  const raw = (new URL(request.url).searchParams.get('q') ?? '').trim();
  const [countries, sectors] = await Promise.all([getCountries().catch(() => []), getSectors().catch(() => [])]);

  let words = tokens(raw);
  const country = countries.find((c) => words.some((w) => w === c.iso3.toLowerCase() || w === fold(c.name_es)));
  if (country) words = words.filter((w) => w !== country.iso3.toLowerCase() && w !== fold(country.name_es));
  const code = words.find((w) => CODE.test(w));
  words = words.filter((w) => w !== code && !CODE_WORDS.has(w));
  const q = words.join(' ');
  const withCountry = (href: string) => (country ? `${href}${href.includes('?') ? '&' : '?'}country=${country.iso3}` : href);

  const groups: Group[] = [];
  if (country && !q && !code) {
    groups.push({ label: `En ${country.name_es}`, items: [
      { label: `Sectores en ${country.name_es}`, href: `/sectores?country=${country.iso3}`, score: 4 },
    ] });
  }

  if (code) {
    const occupations = await apiGet('/occupations', OccupationsSchema, { q: code }, 300).catch(() => []);
    const items = occupations
      .filter((o) => o.occupation_code.startsWith(code) && (!q || matchScore(o.name, q) > 0))
      .sort((a, b) => a.occupation_code.localeCompare(b.occupation_code))
      .slice(0, MAX)
      .map((o) => ({ label: o.name, detail: `CIUO ${o.occupation_code}`, href: withCountry(`/ocupaciones/${o.occupation_code}`), score: 4 }));
    groups.push({ label: 'Ocupaciones', items });
  } else if (q.length >= MIN_CHARS) {
    const [indicators, occupations, skills] = await Promise.all([
      getIndicators().catch(() => []),
      apiGet('/occupations', OccupationsSchema, { q }, 300).catch(() => []),
      apiGet('/skills', SkillsSchema, { q, limit: CANDIDATES }, 300).catch(() => []),
    ]);
    groups.push(
      { label: 'Indicadores', items: ranked(indicators.map((i) => ({ label: i.name, detail: i.domain_label, href: `/panorama?indicator=${i.code}`, score: matchScore(i.name, q) }))) },
      { label: 'Ocupaciones', items: ranked(occupations.map((o) => ({ label: o.name, detail: `CIUO ${o.occupation_code}`, href: withCountry(`/ocupaciones/${o.occupation_code}`), score: matchScore(o.name, q) }))) },
      { label: 'Habilidades', items: ranked(skills.map((s) => ({ label: s.name, href: `/habilidades?q=${encodeURIComponent(s.name)}`, score: matchScore(s.name, q) }))) },
    );
  }

  if (q) {
    groups.push(
      { label: 'Sectores', items: ranked(sectors.map((s) => ({ label: s.name, href: withCountry(`/sectores?sector=${s.sector_code}`), score: matchScore(s.name, q) }))) },
      { label: 'Secciones', items: ranked([...SECTIONS, ...EXTRA_SECTIONS].map((s) => ({ label: s.label, href: s.href, score: matchScore(s.label, q) }))) },
    );
  }

  // orden fijo y predecible; solo sube primero el grupo que tiene una coincidencia exacta ("salud" -> sector Salud)
  const exact = (g: Group) => (g.items.some((i) => i.score === EXACT) ? 0 : 1);
  const order = (g: Group) => GROUP_ORDER.indexOf(g.label) >>> 0;
  const out = groups.filter((g) => g.items.length).sort((a, b) => exact(a) - exact(b) || order(a) - order(b));
  return Response.json({ query: raw, country: country?.name_es ?? null, code: code ?? null, groups: out.map((g) => ({ label: g.label, items: g.items.map((i) => ({ label: i.label, detail: i.detail, href: i.href })) })) });
}
