'use client';

import { useState } from 'react';
import { Minus, Plus } from 'lucide-react';
import type { SkillItem } from '@/lib/schemas/api';
import { cn } from '@/lib/utils';
import { formatNumber } from '@/lib/utils/format';

const INITIAL = 9;

/** Chips de habilidades ESCO con peso y expansión del listado completo. */
export function SkillsCloud({
  skills,
  total,
  visible = INITIAL,
}: {
  skills: SkillItem[];
  total: number;
  visible?: number;
}) {
  const [expanded, setExpanded] = useState(false);
  const shown = expanded ? skills : skills.slice(0, visible);
  const hidden = Math.max(0, total - shown.length);

  return (
    <div>
      <ul className="flex flex-wrap gap-2">
        {shown.map((skill) => (
          <li key={skill.skill_code}>
            <span
              title={skill.skill_type_label ?? 'Habilidad ESCO'}
              className="inline-flex items-center gap-2 rounded-full border border-card-border bg-canvas px-3 py-1.5 text-[11.5px] text-body"
            >
              <span className="max-w-[26rem] truncate">{skill.name}</span>
              {skill.weight !== null && skill.weight !== undefined && (
                <span className="rounded-full bg-surface-2 px-1.5 py-0.5 text-[10px] font-semibold text-muted-text">
                  {formatNumber(skill.weight, 2)}
                </span>
              )}
            </span>
          </li>
        ))}
      </ul>

      {total > visible && (
        <button
          type="button"
          onClick={() => setExpanded((current) => !current)}
          aria-expanded={expanded}
          className={cn(
            'mt-4 inline-flex items-center gap-2 text-[12px] font-semibold text-link transition-colors hover:text-link-hover hover:underline',
            'focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-focus',
          )}
        >
          {expanded ? (
            <>
              <Minus className="size-3.5" aria-hidden />
              Mostrar menos habilidades
            </>
          ) : (
            <>
              <Plus className="size-3.5" aria-hidden />
              Mostrar {hidden} habilidades completas
            </>
          )}
        </button>
      )}
    </div>
  );
}
