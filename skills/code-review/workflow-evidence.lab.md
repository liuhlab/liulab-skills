# Workflow evidence

Check the development process as well as the diff. Report a mismatch as a finding.

- The development agent and behavioral eval agent agree. An unsupported case is explicit,
  never a silent fallback to another agent.
- Evidence identifies the installed version or commit, verified content hash, assertion
  result and transcript. Read the transcript before claiming behavioral verification.
- Installation changes affect only the selected agent and run-owned resources. Failed
  setup or mismatched content launches no eval. Cleanup preserves unrelated user state.
- Existing authorization carries through review, release and cleanup. Routine steps reuse
  approved command prefixes and batch independent work. Necessary sandbox escalation is
  narrow; no bypass or blanket permission change replaces it.
- Any approval-burden claim distinguishes tool calls, escalation requests and actual user
  prompts. An escalation request alone does not prove that the user saw a prompt.

Keep credentials, local connection details and raw private transcripts out of public artifacts.
