# Production Audit: Smoke Test V65

Created: 2026-05-13T10:01:14
Score: 57/100
Verdict: Fix critical blockers before final render

## Fix First
- [ERROR] Assets / Missing asset check: Approve or reuse images for missing scenes
- [WARN] Final Package / Final package checklist: Build final render, clips, captions, and marketing package
- [WARN] Character / Prompt character consistency: Apply character lock to storyboard prompts
- [WARN] TikTok / TikTok package readiness: Generate clips/9:16 render and TikTok caption
- [WARN] YouTube / YouTube package readiness: Render 16:9 and review YouTube copy
- [WARN] Render / Audio source: Add audio file in Render Lab
- [WARN] Render / Final 16:9 render: Render final 16:9 output

## Checks
- OK Narrative / Storyboard exists: 8 scenes found
- OK Narrative / Has setup and ending: roles: breathing_room, emotional_peak, emotional_transition, setup
- OK Narrative / Has emotional peak: peak scene: 6
- OK Narrative / Visual story consistency: score 100
- OK Character / Character profile: character lock metadata present
- WARN Character / Prompt character consistency: average score 6.2
- OK Subtitle / Readable subtitle length: 0 long subtitle lines
- OK Subtitle / Subtitle text coverage: 0 scenes may miss subtitle text
- OK Subtitle / Dynamic subtitle emotion: 8 scenes have emotion style
- OK Hook / Hook candidate: top hook score 95
- OK Hook / Hook clip readiness: 3 TikTok candidates
- WARN Render / Audio source: missing audio
- WARN Render / Final 16:9 render: D:\Project AI\vela_ai_studio_v5\outputs\renders\Smoke_Test_V65\temp_smoke\final_16x9.mp4
- INFO Render / Final 9:16 render: D:\Project AI\vela_ai_studio_v5\outputs\renders\Smoke_Test_V65\temp_smoke\final_9x16.mp4
- ERROR Assets / Missing asset check: missing scenes: 2, 4, 8, 5, 7, 3, 6
- OK Assets / Hero shot selected: hero/approved image available
- WARN TikTok / TikTok package readiness: needs caption or 9:16 render
- WARN YouTube / YouTube package readiness: title/description + 16:9 render
- OK Marketing / Upload checklist: 6 checklist items
- WARN Final Package / Final package checklist: 3/9 ready
