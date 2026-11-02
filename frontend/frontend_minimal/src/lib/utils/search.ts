/**
 * Búsqueda tolerante (la misma regla que el backend en app/core/search.py): cada palabra tiene que
 * coincidir con el comienzo de una palabra del texto, en cualquier orden y sin importar tildes ni
 * plural o género (se busca la raíz: "enfermera" encuentra "enfermería").
 */

const MAX_TOKENS = 6;
/** Terminaciones de plural y género que se sacan para buscar la raíz (la más larga primero). */
const ENDINGS = ['es', 'as', 'os', 'a', 'o', 's'];
const MIN_STEM = 4;
const ACCENTS: Record<string, string> = { a: '[aáàä]', e: '[eéèë]', i: '[iíìï]', o: '[oóòö]', u: '[uúùü]', n: '[nñ]', c: '[cç]' };

export const fold = (s: string) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();

/** Palabras de la búsqueda, en minúsculas, sin tildes ni signos. */
export function tokens(q: string): string[] {
  return fold(q).split(/[^\p{L}\p{N}]+/u).filter(Boolean).slice(0, MAX_TOKENS);
}

/** Raíz para buscar: "enfermeras" → "enfermer", "desarrolladores" → "desarrollador". */
export function stem(word: string): string {
  const end = ENDINGS.find((e) => word.endsWith(e) && word.length - e.length >= MIN_STEM);
  return end ? word.slice(0, -end.length) : word;
}

/** Comienzo de palabra + la palabra con sus variantes acentuadas. */
function tokenRegex(token: string, flags = 'iu'): RegExp {
  return new RegExp(`(?<![\\p{L}\\p{N}])${[...token].map((ch) => ACCENTS[ch] ?? ch).join('')}`, flags);
}

/**
 * Qué tan bien coincide el texto (0 = no coincide). Prioriza el texto igual a la búsqueda, después
 * el que empieza con ella, después la frase completa en el medio y por último las palabras sueltas.
 */
export function matchScore(text: string, q: string): number {
  const words = tokens(q);
  if (!words.length || !words.every((w) => tokenRegex(stem(w)).test(text))) return 0;
  const t = fold(text);
  const phrase = words.join(' ');
  if (t === phrase) return 4;
  if (t.startsWith(phrase)) return 3;
  if (tokenRegex(phrase).test(t)) return 2;
  return 1;
}

/** Corta el texto en partes para resaltar lo que coincide con la búsqueda. */
export function highlight(text: string, q: string): { text: string; hit: boolean }[] {
  const words = tokens(q);
  if (!words.length) return [{ text, hit: false }];
  const marks = new Array<boolean>(text.length).fill(false);
  for (const w of words) {
    for (const m of text.matchAll(tokenRegex(stem(w), 'giu'))) for (let i = m.index; i < m.index + m[0].length; i++) marks[i] = true;
  }
  const parts: { text: string; hit: boolean }[] = [];
  for (let i = 0; i < text.length; i++) {
    const last = parts[parts.length - 1];
    if (last && last.hit === marks[i]) last.text += text[i];
    else parts.push({ text: text[i], hit: marks[i] });
  }
  return parts;
}
