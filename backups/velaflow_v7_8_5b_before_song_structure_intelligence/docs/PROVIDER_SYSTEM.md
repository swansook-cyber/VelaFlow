# Provider System

VelaFlow keeps provider access behind abstraction modules so AI vendors can be
swapped or disabled without breaking the workflow.

## Provider Areas

- Text providers: Gemini and offline/manual fallback
- Image providers: manual/offline, OpenAI images, Flux/SDXL placeholders
- Video providers: manual/offline slots and future external video APIs
- Local fallback: placeholder assets and simplified metadata generation

Provider access is represented by `providers_enabled`.

## Rules

- Never store API keys in project JSON.
- Keep offline/manual fallback working.
- Provider failures should return structured results and not hard-crash pages.
- New providers should plug into the provider abstraction instead of UI code.
