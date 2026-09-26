// Hand-drawn SVG illustrations. Each has a text alternative supplied by the caller.

export function DipIllustration({ title }: { title: string }) {
  return (
    <svg viewBox="0 0 320 150" role="img" aria-label={title} className="h-auto w-full max-w-md">
      <rect x="0" y="0" width="320" height="150" fill="#f0fdfa" rx="12" />
      {/* bank and plants */}
      <path d="M0 70 C60 60 90 75 120 72 L120 150 L0 150 Z" fill="#a3a36b" />
      <path d="M40 72 v-30 M48 72 v-38 M56 72 v-26 M200 95 v-28 M208 95 v-36" stroke="#3f6212" strokeWidth="3" strokeLinecap="round" />
      {/* still water */}
      <path d="M120 72 C170 80 230 88 320 86 L320 150 L120 150 Z" fill="#7dd3fc" />
      <path d="M140 95 h40 M200 110 h50 M250 128 h40" stroke="#e0f2fe" strokeWidth="3" strokeLinecap="round" />
      {/* arm and cup entering at an angle */}
      <path d="M40 30 L140 70" stroke="#fdba74" strokeWidth="12" strokeLinecap="round" />
      <g transform="rotate(35 160 82)">
        <rect x="140" y="70" width="42" height="30" rx="4" fill="#ffffff" stroke="#334155" strokeWidth="2.5" />
        <path d="M143 88 h36" stroke="#38bdf8" strokeWidth="3" />
      </g>
      <text x="230" y="40" fontSize="13" fill="#0f172a">
        still water at the edge
      </text>
      <path d="M232 46 L215 78" stroke="#0f172a" strokeWidth="1.5" markerEnd="url(#a)" />
      <defs>
        <marker id="a" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
          <path d="M0 0 L10 5 L0 10 z" fill="#0f172a" />
        </marker>
      </defs>
    </svg>
  )
}

function Surface() {
  return (
    <>
      <rect x="0" y="0" width="150" height="110" fill="#e0f2fe" rx="10" />
      <rect x="0" y="0" width="150" height="24" fill="#f8fafc" rx="10" />
      <path d="M0 24 H150" stroke="#0369a1" strokeWidth="2.5" />
    </>
  )
}

/** Culex-type larva: body hangs down at an angle from a breathing tube (siphon) at the surface. */
export function PostureAngled({ title }: { title: string }) {
  return (
    <svg viewBox="0 0 150 110" role="img" aria-label={title} className="h-28 w-auto">
      <Surface />
      <g stroke="#334155" strokeLinecap="round" fill="#64748b">
        <path d="M78 24 L88 44" strokeWidth="3" />
        <ellipse cx="72" cy="62" rx="8" ry="22" transform="rotate(-30 72 62)" />
        <circle cx="56" cy="86" r="8" />
      </g>
    </svg>
  )
}

/** Anopheles-type larva: lies flat, parallel to and just under the surface. */
export function PostureFlat({ title }: { title: string }) {
  return (
    <svg viewBox="0 0 150 110" role="img" aria-label={title} className="h-28 w-auto">
      <Surface />
      <g stroke="#334155" fill="#64748b">
        <ellipse cx="80" cy="30" rx="34" ry="6" />
        <circle cx="42" cy="30" r="7" />
      </g>
    </svg>
  )
}
