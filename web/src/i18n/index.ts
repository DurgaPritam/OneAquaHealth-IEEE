import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'

export const LANGUAGES = [
  { code: 'en', name: 'English', machine: false },
  { code: 'pt', name: 'Português', machine: true },
  { code: 'it', name: 'Italiano', machine: true },
  { code: 'nl', name: 'Nederlands', machine: true },
  { code: 'no', name: 'Norsk', machine: true },
  { code: 'fr', name: 'Français', machine: true },
] as const

export type LanguageCode = (typeof LANGUAGES)[number]['code']

const loaders: Record<Exclude<LanguageCode, 'en'>, () => Promise<{ default: object }>> = {
  pt: () => import('./locales/pt.json'),
  it: () => import('./locales/it.json'),
  nl: () => import('./locales/nl.json'),
  no: () => import('./locales/no.json'),
  fr: () => import('./locales/fr.json'),
}

const STORAGE_KEY = 'aquasentinel.lang'

function initialLanguage(): LanguageCode {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (saved && LANGUAGES.some((l) => l.code === saved)) return saved as LanguageCode
  } catch {
    /* storage blocked */
  }
  return 'en'
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en } },
  lng: 'en',
  fallbackLng: 'en',
  interpolation: { escapeValue: false },
})

export async function changeLanguage(code: LanguageCode): Promise<void> {
  if (code !== 'en' && !i18n.hasResourceBundle(code, 'translation')) {
    const mod = await loaders[code]()
    i18n.addResourceBundle(code, 'translation', mod.default)
  }
  await i18n.changeLanguage(code)
  document.documentElement.lang = code
  try {
    localStorage.setItem(STORAGE_KEY, code)
  } catch {
    /* storage blocked */
  }
}

const start = initialLanguage()
if (start !== 'en') void changeLanguage(start)

export default i18n
