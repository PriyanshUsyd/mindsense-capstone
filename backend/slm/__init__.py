"""SLM integration package (Ollama + phi4-mini:3.8b). See model_manifest.yaml
and prompts/ — all prompts load via yaml.safe_load into a strict Pydantic
PromptManifest, per skills/slm-ollama.md. All Ollama calls route through
client.py (not yet built — Richard Zhao's Week 5 task per Weekly_Plan.md)."""
