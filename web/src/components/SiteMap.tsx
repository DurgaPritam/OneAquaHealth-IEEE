import 'leaflet/dist/leaflet.css'
import { CircleMarker, MapContainer, TileLayer, Tooltip, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import type { Site } from '../lib/types'

export interface MapPoint {
  site: Site
  colour?: string
  label?: string
}

function FitBounds({ points }: { points: MapPoint[] }) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    const lats = points.map((p) => p.site.lat)
    const lons = points.map((p) => p.site.lon)
    map.fitBounds(
      [
        [Math.min(...lats), Math.min(...lons)],
        [Math.max(...lats), Math.max(...lons)],
      ],
      { padding: [24, 24], maxZoom: 14 },
    )
  }, [map, points])
  return null
}

/** Leaflet map of sites. Decorative for screen readers: every map has a list alternative next to it. */
export default function SiteMap({
  points,
  selectedId,
  onSelect,
  label,
  height = 320,
}: {
  points: MapPoint[]
  selectedId?: string
  onSelect?: (id: string) => void
  label: string
  height?: number
}) {
  return (
    <div role="img" aria-label={label} className="overflow-hidden rounded-xl border border-slate-200" style={{ height }}>
      <MapContainer center={[48, 5]} zoom={4} scrollWheelZoom={false} style={{ height: '100%', width: '100%' }} keyboard={false}>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        {points.map((p) => (
          <CircleMarker
            key={p.site.id}
            center={[p.site.lat, p.site.lon]}
            radius={p.site.id === selectedId ? 11 : 8}
            pathOptions={{
              color: p.site.id === selectedId ? '#053a30' : '#ffffff',
              weight: p.site.id === selectedId ? 4 : 2,
              fillColor: p.colour ?? '#0b7a66',
              fillOpacity: 0.9,
            }}
            eventHandlers={onSelect ? { click: () => onSelect(p.site.id) } : undefined}
          >
            <Tooltip>{p.label ?? `${p.site.id} ${p.site.name}`}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
    </div>
  )
}
