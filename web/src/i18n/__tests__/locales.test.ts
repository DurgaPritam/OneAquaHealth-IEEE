import { describe, expect, it } from 'vitest'
import en from '../locales/en.json'
import fr from '../locales/fr.json'
import it_ from '../locales/it.json'
import nl from '../locales/nl.json'
import no from '../locales/no.json'
import pt from '../locales/pt.json'

type Tree = { [k: string]: string | Tree }

function paths(tree: Tree, prefix = ''): string[] {
  return Object.entries(tree).flatMap(([k, v]) => (typeof v === 'string' ? [prefix + k] : paths(v, `${prefix}${k}.`)))
}

function values(tree: Tree): string[] {
  return Object.values(tree).flatMap((v) => (typeof v === 'string' ? [v] : values(v)))
}

const placeholders = (s: string) => (s.match(/{{\w+}}/g) ?? []).sort().join(',')

describe('locales', () => {
  const enPaths = paths(en as Tree).sort()
  for (const [code, tree] of Object.entries({ pt, it: it_, nl, no, fr })) {
    it(`${code} has exactly the English keys and placeholders`, () => {
      expect(paths(tree as Tree).sort()).toEqual(enPaths)
      const flatEn = Object.fromEntries(enPaths.map((p) => [p, p.split('.').reduce<any>((o, k) => o[k], en)]))
      for (const p of enPaths) {
        const v = p.split('.').reduce<any>((o, k) => o[k], tree)
        expect(placeholders(v), `${code}:${p}`).toBe(placeholders(flatEn[p]))
      }
    })
  }
  it('no locale uses em-dashes or en-dashes', () => {
    for (const tree of [en, pt, it_, nl, no, fr]) for (const v of values(tree as Tree)) expect(v).not.toMatch(/[—–]/)
  })
})
