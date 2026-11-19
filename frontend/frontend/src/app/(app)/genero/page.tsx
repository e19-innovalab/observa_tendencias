import type { Metadata } from 'next';
import { connection } from 'next/server';
import { Suspense } from 'react';
import { GenderView } from '@/components/data/GenderView';
import { PageSkeleton } from '@/components/data/PageSkeleton';
import { Page } from '@/components/data/ui';
import { PageHero } from '@/components/ui/layout/PageHero';

export const metadata: Metadata = { title: 'Género' };

type SearchParams = {
  country?: string;
  anio?: string;
  sector_kpi?: string;
};

async function Datos({ searchParams }: { searchParams: Promise<SearchParams> }) {
  // Es una página privada con datos vivos: no debe servirse desde caché estática.
  await connection();
  const sp = await searchParams;
  return <GenderView sp={sp} />;
}

export default function GeneroPage({
  searchParams,
}: {
  searchParams: Promise<SearchParams>;
}) {
  return (
    <>
      <PageHero
        title="Género"
        description="Participación de las mujeres en la formación y el empleo por sector, sus brechas y el diagnóstico de paridad en Argentina, Chile y Uruguay."
      />
      <Page>
        <div className="space-y-6">
          <Suspense fallback={<PageSkeleton />}>
            <Datos searchParams={searchParams} />
          </Suspense>
        </div>
      </Page>
    </>
  );
}
