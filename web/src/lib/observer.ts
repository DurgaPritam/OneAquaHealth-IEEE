const KEY = 'aquasentinel.observer'
const ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

/** Random pseudonymous code, same format as the API (OBS- plus six characters). */
export function newObserverCode(random: () => number = Math.random): string {
  let code = 'OBS-'
  for (let i = 0; i < 6; i += 1) code += ALPHABET[Math.floor(random() * ALPHABET.length)]
  return code
}

/** The device's observer code. Created locally so the first check-in works offline. */
export function getObserverCode(storage: Storage = localStorage): string {
  try {
    const existing = storage.getItem(KEY)
    if (existing && /^OBS-[A-Z0-9]{6}$/.test(existing)) return existing
    const code = newObserverCode(() => crypto.getRandomValues(new Uint32Array(1))[0] / 2 ** 32)
    storage.setItem(KEY, code)
    return code
  } catch {
    return newObserverCode()
  }
}

/** Distance in metres between two points (haversine). */
export function distanceM(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const r = 6371000
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return 2 * r * Math.asin(Math.sqrt(a))
}

/** Round to about 100 m before anything leaves the device. */
export function roundCoord(value: number): number {
  return Math.round(value * 1000) / 1000
}
