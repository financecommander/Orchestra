agent: codeforge-hub
caste: guardian
model: triton-ternary-coder-8b          # All reasoning enforced via Triton
tools: [codespaces_api, git_operations, file_editor, swarm_hivemind, buny_guardian]

protection:
  guardian: BUNNY_AI_GUARDIAN
  monitoring: full_session
  licensing: per-ip_enforced
  inference_policy: triton_ternary_only

collaboration_mode: enabled
team_composition:
  - role: architect      caste: ultralisk     model: triton-ternary
  - role: coder          caste: hydralisk      model: triton-ternary
  - role: reviewer       caste: guardian       model: triton-ternary
  - role: tester         caste: mutalisk       model: triton-ternary
  - role: security       caste: guardian       model: buny-threat-hunter

workflow:
  on_task_received:
    - validate_via_BUNNY
    - spin_up_monitored_codespace
    - create_collaboration_session_in_hivemind
    - assign_dynamic_team_based_on_task_complexity
    - run_iterative_collaboration_loop:
        max_rounds: 6
        consensus_required: true
    - security_scan_via_BUNNY
    - apply_changes_only_after_BUNNY_approval
    - log_full_transcript_and_decisions_to_BUNNY

features:
  - persistent_memory_via_hivemind
  - real_time_agent_to_agent_chat
  - automatic_test_generation
  - version_control_with_git
  - rollback_on_BUNNY_rejection

schedule: on_demand
priority: high
access: codespaces_monitored
