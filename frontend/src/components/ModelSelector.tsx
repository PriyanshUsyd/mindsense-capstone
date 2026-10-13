interface ModelSelectorProps {
  disabled: boolean
  modelTags: string[]
  onChange: (modelTag: string) => void
  value: string
}

const modelNames: Record<string, string> = {
  'phi4-mini:3.8b': 'Phi-4 Mini · 3.8B',
  'qwen3:4b': 'Qwen 3 · 4B',
}

function modelName(modelTag: string) {
  return modelNames[modelTag] ?? modelTag
}

export function ModelSelector({
  disabled,
  modelTags,
  onChange,
  value,
}: ModelSelectorProps) {
  return (
    <label className="model-selector">
      <span className="model-selector__caption">Model</span>
      <span className="model-selector__control">
        <select
          aria-label="Choose local model"
          disabled={disabled}
          onChange={(event) => onChange(event.target.value)}
          value={value}
        >
          {modelTags.map((modelTag) => (
            <option key={modelTag} value={modelTag}>
              {modelName(modelTag)}
            </option>
          ))}
        </select>
        <span aria-hidden="true" className="model-selector__chevron">⌄</span>
      </span>
    </label>
  )
}
