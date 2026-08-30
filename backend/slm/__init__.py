"""Local SLM integration for evidence-constrained MindSense responses.

Phi-4 Mini and Qwen3 are comparison candidates, not final selections. Runtime
calls are loopback-only through :mod:`backend.slm.client`; versioned prompts,
deterministic safety validation, and safe fallback orchestration live in this
package.
"""
