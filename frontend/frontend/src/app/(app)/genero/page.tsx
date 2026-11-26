import type { Metadata } from 'next';
import { connection } from 'next/server';
import { Suspense } from 'react';
import { GenderView, type GenderTab } from '@/components/data/GenderView';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import { Page } from '@/components/data/ui';
import { PageHero } from '@/components/ui/layout/PageHero';
import { SectionTabs } from '@/components/ui/navigation/SectionTabs';

export const metadata: Metadata = { title: 'Género' };

type SearchParams = {
  country?: string;
  anio?: string;
  sector_kpi?: string;
  tab?: string;
};

const TABS = [
  { id: 'titulados', label: 'Titulados por sexo' },
  { id: 'ocupados', label: 'Personas ocupadas y salarios' },
];

async function Datos({
  searchParams,
  tab,
}: {
  searchParams: Promise<SearchParams>;
  tab: GenderTab;
}) {
  // Es una página privada con datos vivos: no debe servirse desde caché estática.
  await connection();
  const sp = await searchParams;
  return <GenderView sp={sp} tab={tab} />;
}

export default async function GeneroPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  const sp = await searchParams;
  const tab: GenderTab = sp.tab === 'ocupados' ? 'ocupados' : 'titulados';

  return (
    <>
      <PageHero
        title="Género"
        description="Participación de las mujeres en la formación y el empleo por sector, sus brechas y el diagnóstico de paridad en Argentina, Chile y Uruguay."
      />
      <Page>
        <div className="space-y-6">
          <SectionTabs tabs={TABS} active={tab} />
          <Suspense fallback={<PageSkeleton />}>
            <Datos searchParams={searchParams} tab={tab} />
          </Suspense>
        </div>
      </Page>
    </>
  );
}
