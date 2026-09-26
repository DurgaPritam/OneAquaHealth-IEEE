export const MAX_EDGE = 1600

/** Target size that keeps the aspect ratio and caps the longest edge. */
export function fitWithin(width: number, height: number, maxEdge = MAX_EDGE): { width: number; height: number } {
  const scale = Math.min(1, maxEdge / Math.max(width, height))
  return { width: Math.round(width * scale), height: Math.round(height * scale) }
}

/**
 * Re-encode a photo through a canvas. Drawing pixels to a canvas and exporting
 * a new JPEG drops every EXIF field, including GPS. Orientation is applied first
 * so the image does not turn sideways once the orientation tag is gone.
 */
export async function sanitisePhoto(file: Blob, maxEdge = MAX_EDGE): Promise<Blob> {
  const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
  const { width, height } = fitWithin(bitmap.width, bitmap.height, maxEdge)
  const canvas = document.createElement('canvas')
  canvas.width = width
  canvas.height = height
  const ctx = canvas.getContext('2d')
  if (!ctx) throw new Error('Canvas not available')
  ctx.drawImage(bitmap, 0, 0, width, height)
  bitmap.close()
  return new Promise((resolve, reject) =>
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error('Could not encode photo'))), 'image/jpeg', 0.85),
  )
}
