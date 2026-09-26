import snapshot from '../../public/demo/snapshot.json'
import { LocalClient, type Snapshot } from '../lib/local/LocalClient'

let n = 0

/** A LocalClient over the real demo snapshot, with its own IndexedDB. */
export function localClient(): LocalClient {
  return new LocalClient(async () => structuredClone(snapshot) as unknown as Snapshot, `demo-test-${n++}`)
}
