# Aureon Capability Stress Audit

- status: capability_stress_audit_needs_attention
- cases: 4
- passed: 3
- expected blocked: 1
- fake passes: 0
- legacy findings: 2

## Cases
- barcode_label_tool: ok=True handover=True kind=barcode_label_generator score=0.96 url=/aureon_adaptive_skills/build_a_local_barcode_label_generator_tool_for_t_09c8258bd8ac/index.html
- interactive_game: ok=True handover=True kind=html_game score=0.94 url=/aureon_generated_apps/make_me_a_game_where_a_man_walks_up_to_a_glowing_ecd9bf4b3ac7.html
- short_video_preview: ok=False handover=False kind=video score=0.429 url=/aureon_visual_artifacts/dog_running_across_the_screen_f038913b5292.mp4
- generic_unknown_tool_gate: ok=True handover=False kind=adaptive_skill_capsule score=0.68 url=/aureon_adaptive_skills/build_a_local_quantum_spline_inventory_generator_95e408c72e6e/index.html

## Findings
- high: Old barcode tool artifact was a generic adaptive capsule (C:\Users\user\aureon-trading\frontend\public\aureon_adaptive_skills\build_a_local_barcode_label_generator_tool_for_t_a390ed39c350\skill.json)
- high: Old barcode tool artifact was a generic adaptive capsule (C:\Users\user\aureon-trading\frontend\public\aureon_adaptive_skills\build_a_local_barcode_label_generator_tool_for_t_b5884c33262e\skill.json)
