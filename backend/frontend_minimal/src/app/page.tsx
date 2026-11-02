import { ArrowRight, BarChart3, Database, GitCompareArrows, LineChart, Search, ShieldCheck, Sparkles, Users } from 'lucide-react';
import type { Metadata } from 'next';
import Link from 'next/link';
import { Suspense } from 'react';
import { Logo } from '@/components/brand/Logo';
import { DEFAULT_SECTOR_STYLE, SECTOR_STYLE } from '@/components/sectors/sectorIcons';
import { getCountries, getDashboardSummary, getSectors } from '@/lib/api/common';
import { getOccupations } from '@/lib/api/skills';
import { getSources } from '@/lib/api/sources';
import { formatDate, formatValue } from '@/lib/utils/format';

export const metadata: Metadata = { title: 'Observa Tendencias · Observatorio del mercado laboral del Cono Sur' };

const ENTER = '/inicio'; // sin sesión, el proxy manda al login y vuelve acá

/** Qué fuente cubre qué país (texto de la landing; el resto se considera regional). */
const SOURCE_SCOPE: Record<string, string> = {
  datos_argentina: 'ARG',
  sipa_argentina: 'ARG',
  indicadores_cti_argentina: 'ARG',
  simel_chile: 'CHL',
  mifuturo_chile: 'CHL',
  bcentral_chile: 'CHL',
  ine_uruguay: 'URY',
  mec_uruguay: 'URY',
};

const FEATURES = [
  { title: 'Ocupaciones', text: 'Las 436 ocupaciones de la CIUO-08 con su índice de empleabilidad, demanda, salario y exposición a la IA generativa.', verb: 'Explorá', icon: Search, href: '/ocupaciones' },
  { title: 'Tendencias y proyecciones', text: 'Hacia dónde se mueve cada indicador y una proyección orientativa de los próximos períodos, con su intervalo.', verb: 'Analizá', icon: LineChart, href: '/tendencias' },
  { title: 'Brechas de habilidades', text: 'Qué habilidades se demandan más rápido de lo que se forman, a partir del empleo y de los titulados de cada país.', verb: 'Compará', icon: GitCompareArrows, href: '/habilidades' },
  { title: 'Alertas', text: 'Cambios fuera de lo habitual, cambios de tendencia y fuentes que dejaron de actualizarse, detectados en cada actualización.', verb: 'Detectá', icon: Sparkles, href: '/alertas' },
];

const STEPS = [
  { title: 'Fuentes oficiales', text: 'Se descargan los datos de organismos oficiales e internacionales (OIT, Banco Mundial, institutos de estadística, ministerios) y se guarda cada archivo con su fecha.' },
  { title: 'Análisis', text: 'Se normalizan a clasificaciones comunes (CIUO-08 para ocupaciones, CINE-F 2013 para carreras) y se calculan tendencias, proyecciones, el índice de empleabilidad y las brechas.' },
  { title: 'Resultados', text: 'Cada valor muestra su fuente, su fecha de actualización y la metodología con la que se calculó. Si una fuente cambia un dato, el anterior queda en el historial.' },
];

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-white">
      <header className="sticky top-0 z-30 border-b border-line bg-white/90 backdrop-blur">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-6 px-6 py-3">
          <Logo />
          <nav aria-label="Secciones" className="hidden gap-6 text-sm text-body md:flex">
            <a href="#que-encontras" className="hover:text-heading">Qué podés encontrar</a>
            <a href="#como-funciona" className="hover:text-heading">Cómo funciona</a>
            <a href="#fuentes" className="hover:text-heading">Fuentes</a>
            <a href="#alcance" className="hover:text-heading">Alcance</a>
          </nav>
          <Link href={ENTER} className="rounded-md bg-brand px-4 py-2 text-sm font-semibold text-white hover:bg-brand-hover">Ingresar</Link>
        </div>
      </header>

      <main>
        <section className="bg-surface">
          <div className="mx-auto grid max-w-7xl items-center gap-10 px-6 py-20 lg:grid-cols-2">
            <div>
              <p className="text-xs font-semibold uppercase tracking-widest text-brand">Observatorio de tendencias laborales y educativas</p>
              <h1 className="mt-3 text-4xl font-bold tracking-tight text-heading md:text-5xl">Explorá, analizá y tomá decisiones</h1>
              <p className="mt-5 max-w-xl text-lg text-body">
                Información socioeconómica, laboral y educativa de Argentina, Chile y Uruguay en un solo lugar, para detectar tendencias, comprender brechas y anticipar cambios.
              </p>
              <div className="mt-8 flex flex-wrap gap-3">
                <Link href={ENTER} className="inline-flex items-center gap-2 rounded-md bg-brand px-5 py-3 text-sm font-semibold text-white hover:bg-brand-hover">
                  Explorar el observatorio <ArrowRight className="size-4" aria-hidden />
                </Link>
                <a href="#como-funciona" className="rounded-md border border-line bg-white px-5 py-3 text-sm font-semibold text-heading hover:border-brand">Cómo funciona</a>
              </div>
              <div className="mt-8 flex items-center gap-3 text-sm text-muted-text">
                <span className="flex gap-1.5">
                  {['ARG', 'CHL', 'URY'].map((c) => <span key={c} className="rounded border border-line bg-white px-1.5 py-0.5 text-xs font-semibold text-heading">{c}</span>)}
                </span>
                3 países con datos comparables
              </div>
            </div>
            <Suspense fallback={<div className="h-72 animate-pulse rounded-xl bg-surface-2" />}>
              <LiveSnapshot />
            </Suspense>
          </div>
        </section>

        <section className="mx-auto grid max-w-7xl items-center gap-10 px-6 py-20 lg:grid-cols-2">
          <h2 className="text-3xl font-bold tracking-tight text-heading">
            El mercado laboral cambia. <span className="text-brand">La información también debería anticipar ese cambio.</span>
          </h2>
          <p className="text-lg text-body">
            Los datos sobre empleo, salarios, formación y habilidades están dispersos entre organismos, formatos y clasificaciones distintas. El observatorio los reúne, los hace comparables entre países y explica cómo se calculó cada número.
          </p>
        </section>

        <section id="que-encontras" className="scroll-mt-16 bg-surface py-20">
          <div className="mx-auto max-w-7xl px-6">
            <p className="text-center text-xs font-semibold uppercase tracking-widest text-brand">Qué podés encontrar</p>
            <h2 className="mt-2 text-center text-3xl font-bold tracking-tight text-heading">Una mirada integrada para tomar mejores decisiones</h2>
            <div className="mt-10 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
              {FEATURES.map(({ title, text, verb, icon: Icon, href }) => (
                <Link key={title} href={href} className="group flex flex-col rounded-lg border border-line bg-white p-5 hover:border-brand">
                  <h3 className="font-semibold text-heading">{title}</h3>
                  <p className="mt-2 flex-1 text-sm text-body">{text}</p>
                  <span className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-brand">
                    <Icon className="size-4" aria-hidden /> {verb}
                  </span>
                </Link>
              ))}
            </div>
          </div>
        </section>

        <section id="como-funciona" className="mx-auto max-w-7xl scroll-mt-16 px-6 py-20">
          <p className="text-center text-xs font-semibold uppercase tracking-widest text-brand">Cómo funciona</p>
          <h2 className="mt-2 text-center text-3xl font-bold tracking-tight text-heading">De datos dispersos a información útil</h2>
          <ol className="mt-10 grid gap-8 md:grid-cols-3">
            {STEPS.map((s, i) => (
              <li key={s.title}>
                <span className="flex size-10 items-center justify-center rounded-md bg-brand text-sm font-bold text-white">{String(i + 1).padStart(2, '0')}</span>
                <h3 className="mt-4 font-semibold text-heading">{s.title}</h3>
                <p className="mt-2 text-sm text-body">{s.text}</p>
              </li>
            ))}
          </ol>
        </section>

        <section id="fuentes" className="scroll-mt-16 bg-surface py-20">
          <div className="mx-auto max-w-7xl px-6">
            <p className="text-center text-xs font-semibold uppercase tracking-widest text-brand">Información con respaldo</p>
            <h2 className="mt-2 text-center text-3xl font-bold tracking-tight text-heading">Trazabilidad y fuentes oficiales</h2>
            <p className="mx-auto mt-3 max-w-2xl text-center text-body">
              Cada dato indica su fuente y su fecha, y distingue lo observado de lo calculado y lo proyectado. Lo que no es estadística oficial (por ejemplo, avisos de empleo o series procesadas por el equipo) se señala como tal.
            </p>
            <Suspense fallback={<div className="mt-10 h-48 animate-pulse rounded-lg bg-surface-2" />}>
              <SourcesByCountry />
            </Suspense>
          </div>
        </section>

        <section id="alcance" className="mx-auto max-w-7xl scroll-mt-16 px-6 py-20">
          <Suspense fallback={<div className="h-64 animate-pulse rounded-lg bg-surface-2" />}>
            <Coverage />
          </Suspense>
        </section>

        <section className="bg-heading py-20 text-center text-white">
          <div className="mx-auto max-w-3xl px-6">
            <h2 className="text-3xl font-bold tracking-tight">Comprendé el mercado laboral desde los datos</h2>
            <p className="mt-4 text-white/80">Explorá tendencias, ocupaciones, habilidades y oportunidades a partir de información integrada y verificable.</p>
            <Link href={ENTER} className="mt-8 inline-flex items-center gap-2 rounded-md bg-white px-5 py-3 text-sm font-semibold text-heading hover:bg-surface">
              Ingresar al observatorio <ArrowRight className="size-4" aria-hidden />
            </Link>
          </div>
        </section>
      </main>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-6 py-8 text-sm text-muted-text">
          <Logo />
          <p>Observatorio de tendencias laborales y educativas · Argentina, Chile y Uruguay · InnovaLab</p>
          <Link href="/metodologia/fuentes" className="text-link hover:underline">Metodología y fuentes</Link>
        </div>
      </footer>
    </div>
  );
}

/** Último dato real de un indicador por país (la "demo" del diseño, con datos vivos). */
async function LiveSnapshot() {
  const countries = await getCountries().catch(() => []);
  const summaries = await Promise.all(countries.map((c) => getDashboardSummary(c.iso3).catch(() => null)));
  const card = (iso3: string) => summaries.find((s) => s?.country_iso3 === iso3)?.highlights[0];
  const first = summaries.find((s) => s?.highlights[0])?.highlights[0];
  if (!first) return null;
  return (
    <div className="rounded-xl border border-line bg-white p-6 shadow-sm">
      <p className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-muted-text"><BarChart3 className="size-4" aria-hidden /> Último dato · {first.indicator.name}</p>
      <ul className="mt-5 space-y-4">
        {countries.map((c) => {
          const h = card(c.iso3);
          return (
            <li key={c.iso3} className="flex items-baseline justify-between gap-4 border-b border-line/60 pb-3 last:border-0">
              <span className="font-medium text-heading">{c.name_es}</span>
              <span className="text-right">
                <span className="text-2xl font-semibold text-heading">{h?.current ? formatValue(h.current.value, h.current.unit) : '—'}</span>
                <span className="ml-2 text-xs text-muted-text">{h?.current?.period}</span>
              </span>
            </li>
          );
        })}
      </ul>
      <p className="mt-4 text-xs text-muted-text">
        Fuente: {first.indicator.sources.map((s) => s.name).join(', ')}
        {first.current?.source_updated_at ? ` · actualizado el ${formatDate(first.current.source_updated_at)}` : ''}
      </p>
    </div>
  );
}

async function SourcesByCountry() {
  const [sources, countries] = await Promise.all([getSources(), getCountries()]);
  const withData = sources.filter((s) => s.last_success_at);
  const groups = [
    { key: 'REG', label: 'Regionales e internacionales' },
    ...countries.map((c) => ({ key: c.iso3, label: c.name_es })),
  ];
  return (
    <div className="mt-10 grid gap-5 md:grid-cols-2 lg:grid-cols-4">
      {groups.map((g) => {
        const list = withData.filter((s) => (SOURCE_SCOPE[s.code] ?? 'REG') === g.key);
        return (
          <div key={g.key} className="rounded-lg border border-line bg-white p-5">
            <h3 className="flex items-center gap-2 font-semibold text-heading"><ShieldCheck className="size-4 text-brand" aria-hidden /> {g.label}</h3>
            <ul className="mt-3 space-y-2 text-sm text-body">
              {list.map((s) => <li key={s.code}>{s.name}</li>)}
              {list.length === 0 && <li className="text-muted-text">Sin fuentes con datos todavía.</li>}
            </ul>
          </div>
        );
      })}
    </div>
  );
}

async function Coverage() {
  const [countries, sectors, occupations, sources] = await Promise.all([getCountries(), getSectors(), getOccupations(), getSources()]);
  const featured = occupations.filter((o) => o.is_featured).length;
  const stats = [
    { value: countries.length, label: 'Países', text: countries.map((c) => c.name_es).join(', '), icon: Users },
    { value: sectors.length, label: 'Sectores estratégicos', text: sectors.map((s) => s.name).join(', '), icon: BarChart3 },
    { value: occupations.length, label: 'Ocupaciones CIUO-08', text: `Todos los grupos primarios de la clasificación, ${featured} de ellas destacadas.`, icon: Search },
    { value: sources.filter((s) => s.last_success_at).length, label: 'Fuentes con datos', text: 'Organismos oficiales e internacionales, con fecha de cada descarga.', icon: Database },
  ];
  return (
    <>
      <h2 className="text-3xl font-bold tracking-tight text-heading">{sectors.length} sectores estratégicos y {occupations.length} ocupaciones</h2>
      <p className="mt-2 max-w-2xl text-body">Los sectores se definen por actividad económica (CIIU) y las ocupaciones siguen la clasificación internacional CIUO-08, para que los tres países se puedan comparar.</p>
      <div className="mt-8 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map(({ value, label, text, icon: Icon }) => (
          <div key={label} className="rounded-lg border border-line p-5">
            <Icon className="size-5 text-brand" aria-hidden />
            <p className="mt-3 text-3xl font-bold text-heading">{value}</p>
            <p className="font-semibold text-heading">{label}</p>
            <p className="mt-1 text-sm text-muted-text">{text}</p>
          </div>
        ))}
      </div>
      <ul className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {sectors.map((s) => {
          const style = SECTOR_STYLE[s.sector_code] ?? DEFAULT_SECTOR_STYLE;
          const Icon = style.icon;
          return (
            <li key={s.sector_code} className="rounded-lg border border-line p-4">
              <span className="flex size-9 items-center justify-center rounded-md" style={{ background: style.soft, color: style.color }}><Icon className="size-5" aria-hidden /></span>
              <p className="mt-3 font-semibold text-heading">{s.name}</p>
              <p className="mt-1 text-xs text-muted-text">CIIU {s.isic_codes.join(', ')}</p>
            </li>
          );
        })}
      </ul>
    </>
  );
}
