import type { Metadata } from 'next';
import Link from 'next/link';
import {
  ArrowRight,
  BarChart3,
  Compass,
  Gauge,
  GitCompare,
  Laptop,
  Microscope,
  Search,
  Stethoscope,
  TrendingUp,
  Zap,
} from 'lucide-react';
import { PublicHeader } from '@/components/ui/layout/PublicHeader';

export const metadata: Metadata = { title: 'Bienvenida' };

const box = 'mx-auto w-full max-w-7xl px-4 sm:px-6';
const titulo = 'text-3xl font-bold tracking-tight text-heading md:text-4xl';
const etiqueta = 'text-xs font-semibold uppercase tracking-widest text-brand';
const btn =
  'inline-flex items-center gap-2 rounded-md bg-brand px-5 py-3 text-sm font-medium text-white hover:bg-brand-hover focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus';

const paises = ['ARG', 'CHL', 'URY'];

const encontrar = [
  { titulo: 'Ocupaciones', texto: 'Conocé la evolución y las oportunidades asociadas a distintas ocupaciones.', accion: 'Explorá', href: '/ocupaciones', icono: Search },
  { titulo: 'Tendencias y proyecciones', texto: 'Analizá cómo evolucionan los principales indicadores e identificá posibles escenarios futuros.', accion: 'Analizá', href: '/tendencias', icono: TrendingUp },
  { titulo: 'Brechas de habilidades', texto: 'Compará las habilidades demandadas por el mercado con la oferta formativa disponible.', accion: 'Compará', href: '/habilidades', icono: GitCompare },
  { titulo: 'Índice de empleabilidad', texto: 'Consultá un índice orientativo construido a partir de variables previamente definidas.', accion: 'Detectá', href: '/ocupaciones', icono: Gauge },
];

const pasos = [
  { num: '01', titulo: 'Fuentes oficiales', texto: 'Conectamos APIs y datasets de organismos públicos de los tres países.' },
  { num: '02', titulo: 'Análisis', texto: 'Normalizamos los datos y calculamos indicadores, tendencias y brechas.' },
  { num: '03', titulo: 'Resultados', texto: 'Mostramos todo en gráficos claros, con la fuente y la fecha de cada dato.' },
];

const fuentes = [
  {
    code: 'ARG',
    pais: 'Argentina',
    color: 'bg-country-arg',
    items: [
      ['INDEC - EPH Continua:', '31 aglomerados urbanos normalizados según factor de expansión Censo 2022.'],
      ['Datos Argentina (API):', 'Registro de empleo registrado privado (SIPA).'],
      ['Sec. de Educación:', 'Anuarios universitarios y títulos emitidos.'],
    ],
  },
  {
    code: 'CHL',
    pais: 'Chile',
    color: 'bg-country-chl',
    items: [
      ['INE Chile - ENE Trimestre Móvil:', 'Calibración con estimaciones censales y ponderación regional.'],
      ['SIMEL Chile API:', 'Indicadores del mercado laboral e informalidad.'],
      ['SABE SENCE & SIES MINEDUC:', 'Matrícula formativa técnica y empleabilidad.'],
    ],
  },
  {
    code: 'URY',
    pais: 'Uruguay',
    color: 'bg-country-ury',
    items: [
      ['INE Uruguay - ECH Longitudinal:', 'Panel con rotación mensual y microdatos de ingresos de los hogares.'],
      ['CEPALSTAT & ILOSTAT:', 'Validación multilateral y homogeneización de tasas.'],
      ['ANEP & UdelaR:', 'Flujos de graduación terciaria y formación dual.'],
    ],
  },
];

const numeros = [
  { valor: '3', titulo: 'Países', texto: 'Argentina, Uruguay y Chile bajo nomenclaturas homogéneas.' },
  { valor: '5', titulo: 'Sectores', texto: 'Tech, Salud, Energía, Turismo y Economía del Conocimiento.' },
  { valor: '25', titulo: 'Ocupaciones', texto: 'Detección de brechas formativas y riesgo de obsolescencia.' },
  { valor: '+10', titulo: 'Fuentes oficiales', texto: 'APIs y datasets trazables.' },
];

const sectores = [
  { nombre: 'Tecnología', texto: 'Software, Cloud, Ciberseguridad.', clave: 'DevOps, Cloud Architect, Data Engineer.', icono: Laptop, color: 'bg-sector-tech-soft text-sector-tech' },
  { nombre: 'Salud', texto: 'Personal clínico, bioestadística y telemedicina.', clave: 'Enfermería UTI, Imagenología, Gestión Sanitaria.', icono: Stethoscope, color: 'bg-sector-health-soft text-sector-health' },
  { nombre: 'Energía', texto: 'Renovables, litio, hidrógeno verde e infraestructura.', clave: 'Técnico Eólico/Solar, Operador Planta Litio.', icono: Zap, color: 'bg-sector-energy-soft text-sector-energy' },
  { nombre: 'Turismo', texto: 'Servicios de hospitalidad, ecoturismo y gastronomía de valor.', clave: 'Gestión Hotelera Sostenible, Guía Bilingüe.', icono: Compass, color: 'bg-sector-tourism-soft text-sector-tourism' },
  { nombre: 'Econ. Conocimiento', texto: 'Servicios jurídicos, contables, I+D y diseño global.', clave: 'Consultoría FinTech, Especialista Patentes.', icono: Microscope, color: 'bg-sector-knowledge-soft text-sector-knowledge' },
];

function Ventana({ children }: { children: React.ReactNode }) {
  return (
    <div className="overflow-hidden rounded-xl border border-line bg-canvas shadow-sm">
      <div className="flex gap-1.5 border-b border-line px-4 py-3" aria-hidden>
        <span className="size-2.5 rounded-full bg-line" />
        <span className="size-2.5 rounded-full bg-line" />
        <span className="size-2.5 rounded-full bg-line" />
      </div>
      {children}
    </div>
  );
}

function Paises({ claro = false }: { claro?: boolean }) {
  return (
    <div className="flex gap-2">
      {paises.map((p) => (
        <span
          key={p}
          className={`rounded border px-1.5 py-0.5 text-[10px] font-semibold tracking-wider ${claro ? 'border-white/30 text-white' : 'border-line text-heading'}`}
        >
          {p}
        </span>
      ))}
    </div>
  );
}

export default function LandingPage() {
  return (
    <>
      <PublicHeader />
      <main className="flex-1">
        <section className="bg-surface-alt py-20">
          <div className={`${box} grid items-center gap-12 lg:grid-cols-2`}>
            <div className="space-y-6">
              <p className={etiqueta}>Observatorio predictivo</p>
              <h1 className="text-4xl font-bold leading-tight tracking-tight text-heading md:text-5xl">
                Explorá, analizá
                <br />
                y tomá decisiones
              </h1>
              <p className="max-w-md text-muted-text">
                Integramos información socioeconómica, laboral y educativa para detectar tendencias, comprender brechas y tomar mejores decisiones.
              </p>
              <div className="flex flex-wrap gap-3">
                <Link href="/inicio" className={btn}>
                  Explorar el Observatorio
                  <ArrowRight className="size-4" aria-hidden />
                </Link>
                <Link
                  href="#funciona"
                  className="rounded-md border border-brand px-5 py-3 text-sm font-medium text-brand hover:bg-surface-2 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus"
                >
                  Cómo funciona
                </Link>
              </div>
              <div className="flex items-center gap-4">
                <Paises />
                <div className="text-xs">
                  <p className="font-semibold text-heading">3 países conectados</p>
                  <p className="text-muted-text">Datos públicos, comparables y trazables</p>
                </div>
              </div>
            </div>
            <Ventana>
              <div className="flex aspect-[4/3] items-center justify-center bg-surface-2">
                <BarChart3 className="size-16 text-brand/40" aria-hidden />
              </div>
            </Ventana>
          </div>
        </section>

        <section id="observatorio" className="scroll-mt-20 py-20">
          <div className={`${box} grid items-center gap-12 lg:grid-cols-2`}>
            <div className="space-y-5">
              <h2 className={titulo}>
                El mercado laboral cambia.
                <br />
                La información también debería anticipar ese cambio.
              </h2>
              <p className="text-muted-text">
                El mercado laboral cambia constantemente. Sin embargo, la información necesaria para comprender estos cambios se encuentra distribuida entre diferentes organismos, datasets e indicadores.
              </p>
            </div>
            <div className="aspect-video rounded-xl bg-surface-2" aria-hidden />
          </div>
        </section>

        <section id="encontrar" className="scroll-mt-20 bg-surface-2 py-20">
          <div className={`${box} space-y-10`}>
            <div className="space-y-3 text-center">
              <p className={etiqueta}>Qué podés encontrar</p>
              <h2 className={titulo}>Una mirada integrada para tomar mejores decisiones</h2>
              <p className="text-muted-text">
                Explorá el mercado laboral desde diferentes perspectivas y entendé no solo qué pasó, sino también qué está cambiando.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {encontrar.map((e) => (
                <div key={e.titulo} className="flex flex-col justify-between gap-5">
                  <div className="h-full space-y-2 rounded-xl bg-canvas p-5">
                    <h3 className="font-semibold text-heading">{e.titulo}</h3>
                    <p className="text-sm text-muted-text">{e.texto}</p>
                  </div>
                  <Link href={e.href} className="inline-flex items-center gap-2 px-1 text-sm font-semibold text-link hover:text-link-hover">
                    <e.icono className="size-4" aria-hidden />
                    {e.accion}
                  </Link>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section id="funciona" className="scroll-mt-20 py-20">
          <div className={`${box} space-y-10`}>
            <div className="space-y-3 text-center">
              <p className={etiqueta}>Cómo funciona</p>
              <h2 className={titulo}>De datos dispersos a información útil</h2>
              <p className="mx-auto max-w-2xl text-muted-text">
                El mercado laboral cambia constantemente. Sin embargo, la información necesaria para comprender estos cambios se encuentra distribuida entre diferentes organismos, datasets e indicadores.
              </p>
            </div>
            <ol className="grid gap-8 md:grid-cols-3">
              {pasos.map((p) => (
                <li key={p.num} className="space-y-3">
                  <span className="inline-flex size-10 items-center justify-center rounded-lg bg-brand text-sm font-bold text-white">{p.num}</span>
                  <h3 className="font-semibold text-heading">{p.titulo}</h3>
                  <p className="text-sm text-muted-text">{p.texto}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="bg-surface-alt py-20">
          <div className={`${box} space-y-10`}>
            <div className="space-y-3 text-center">
              <p className={etiqueta}>Explorá los datos - Demo</p>
              <h2 className={titulo}>¿Qué está pasando en el mercado laboral?</h2>
              <p className="text-muted-text">Consultá indicadores y descubrí cómo evolucionan sectores, ocupaciones y habilidades.</p>
            </div>
            <Ventana>
              <div className="flex aspect-[16/7] flex-col items-center justify-center gap-3 bg-surface p-6 text-center text-sm text-muted-text">
                <TrendingUp className="size-10 text-brand/40" aria-hidden />
                Vista previa del panorama regional
              </div>
            </Ventana>
            <div className="text-center">
              <Link href="/panorama-regional" className={btn}>
                Explorar el Observatorio
                <ArrowRight className="size-4" aria-hidden />
              </Link>
            </div>
          </div>
        </section>

        <section className="py-20">
          <div className={`${box} space-y-10`}>
            <div className="space-y-3 text-center">
              <p className={etiqueta}>Información con respaldo</p>
              <h2 className={titulo}>Trazabilidad y fuentes oficiales</h2>
              <p className="text-muted-text">
                El Observatorio identifica fuentes, fechas de actualización y distingue datos observados, indicadores y proyecciones.
              </p>
            </div>
            <div className="grid gap-6 lg:grid-cols-[2fr_1fr]">
              <div className="space-y-4">
                {fuentes.map((f) => (
                  <div key={f.code} className="space-y-3 rounded-xl border border-line p-5">
                    <div className="flex items-center gap-3">
                      <span className={`size-2.5 rounded-full ${f.color}`} aria-hidden />
                      <h3 className="font-semibold text-heading">{f.pais}</h3>
                      <span className="text-xs font-semibold tracking-wider text-muted-text">{f.code}</span>
                    </div>
                    <ul className="space-y-1.5 text-xs text-muted-text">
                      {f.items.map(([nombre, texto]) => (
                        <li key={nombre}>
                          <strong className="text-body">{nombre}</strong> {texto}
                        </li>
                      ))}
                    </ul>
                  </div>
                ))}
              </div>
              <div className="flex flex-col items-center justify-center gap-1 rounded-xl bg-surface-2 p-8 text-center">
                <p className="text-5xl font-bold text-brand">100%</p>
                <p className="text-lg font-semibold text-brand">Oficial</p>
                <p className="text-xs uppercase tracking-widest text-muted-text">Trazabilidad total</p>
              </div>
            </div>
          </div>
        </section>

        <section id="alcance" className="scroll-mt-20 bg-surface-2 py-20">
          <div className={`${box} space-y-10`}>
            <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
              <h2 className={`${titulo} max-w-xl`}>5 sectores estratégicos y 25 ocupaciones monitoreadas</h2>
              <p className="max-w-sm text-sm text-muted-text">
                Sectores seleccionados por su tracción transfronteriza, capacidad exportadora y necesidad crítica de reconversión de habilidades.
              </p>
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {numeros.map((n) => (
                <div key={n.titulo} className="space-y-1 rounded-xl bg-canvas p-5">
                  <p className="text-3xl font-bold text-brand">{n.valor}</p>
                  <p className="font-semibold text-heading">{n.titulo}</p>
                  <p className="text-sm text-muted-text">{n.texto}</p>
                </div>
              ))}
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
              {sectores.map((s) => (
                <div key={s.nombre} className="space-y-3 rounded-xl bg-canvas p-5">
                  <span className={`inline-flex size-10 items-center justify-center rounded-lg ${s.color}`}>
                    <s.icono className="size-5" aria-hidden />
                  </span>
                  <h3 className="font-semibold text-heading">{s.nombre}</h3>
                  <p className="text-sm text-muted-text">{s.texto}</p>
                  <div className="space-y-1 border-t border-line pt-3">
                    <p className="text-[10px] font-semibold uppercase tracking-widest text-muted-text">Ocupaciones clave</p>
                    <p className="text-sm text-body">{s.clave}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="bg-brand-deep py-20 text-white">
          <div className={`${box} space-y-6 text-center`}>
            <p className="inline-block rounded-full border border-white/30 px-3 py-1 text-[10px] font-semibold uppercase tracking-widest">
              Acceso abierto institucional · Licencia ODC-BY
            </p>
            <h2 className="text-3xl font-bold tracking-tight md:text-5xl">
              Comprendé el mercado laboral
              <br />
              desde los datos.
            </h2>
            <p className="text-white/80">Explorá tendencias, ocupaciones, habilidades y oportunidades a partir de información integrada.</p>
            <Link
              href="/login"
              className="inline-block rounded-md bg-white px-6 py-3 text-sm font-medium text-brand-deep hover:bg-white/90 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white"
            >
              Ingresar al Observatorio
            </Link>
          </div>
        </section>
      </main>

      <footer className="bg-heading py-12 text-sm text-white/70">
        <div className={`${box} space-y-8`}>
          <div className="flex flex-col items-center gap-4 text-center">
            <p className="flex items-center gap-2 text-lg font-bold text-white">
              <BarChart3 className="size-5" aria-hidden />
              Observa Tendencias
            </p>
            <p className="max-w-md">
              Iniciativa para la integración, armonización y difusión de estadísticas socioeconómicas, laborales y formativas en el Cono Sur.
            </p>
            <Paises claro />
          </div>
          <div className="flex flex-col justify-between gap-2 border-t border-white/10 pt-6 text-xs md:flex-row">
            <p>© 2026 Observatorio de Tendencias Socioeconómicas del Cono Sur.</p>
            <p>Versión MVP</p>
          </div>
        </div>
      </footer>
    </>
  );
}
