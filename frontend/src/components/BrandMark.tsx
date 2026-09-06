import leafMark from '../assets/mindsense-leaf.svg'

interface BrandMarkProps {
  compact?: boolean
}

export function BrandMark({ compact = false }: BrandMarkProps) {
  return (
    <span className="brand-mark">
      <img src={leafMark} width="44" height="44" alt="" />
      {!compact && (
        <span className="brand-copy">
          <strong>MindSense</strong>
          <small>Wellbeing companion</small>
        </span>
      )}
    </span>
  )
}
