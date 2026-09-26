import axe from 'axe-core'

/**
 * Run axe on a rendered container. jsdom cannot compute colours, so the
 * colour-contrast rule is checked in the Playwright suite instead.
 */
export async function axeViolations(container: Element) {
  const result = await axe.run(container, { rules: { 'color-contrast': { enabled: false } } })
  return result.violations.map((v) => `${v.id}: ${v.help} (${v.nodes.map((n) => n.target.join(' ')).join(', ')})`)
}
