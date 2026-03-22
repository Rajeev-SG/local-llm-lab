# Agent Offload Role Proof

- Date: 2026-03-22
- Target flow: In Open WebUI, select the tuned `local-helper-fast:latest` role model, enter a prompt, submit it, and confirm the browser shows a clean final answer without a visible reasoning trace in the transcript.
- Target URL: `http://localhost:3001`

## Expected Behavior

- The `local-helper-fast:latest` Open WebUI model should route to `qwen3.5:9b` with `think=false`.
- A prompt entered in the browser should produce a usable final answer.
- The transcript should not show a reasoning block for this role.

## Observed Behavior

- Pass.
- In a fresh browser session, the model selector showed `Local Helper Fast` as the selected model.
- Prompt entered: `What is 17 + 26? Reply with digits only.`
- The final chat transcript rendered `"43"` for `Local Helper Fast`.
- The desktop and mobile snapshots both show the final answer in the transcript with no visible reasoning block attached to the assistant reply.
- Supporting API check through Open WebUI also returned `content: "43"` and `reasoning: null` for `model: "local-helper-fast:latest"`.

## Evidence

- Desktop transcript snapshot: `/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/desktop-final.yml`
- Desktop screenshot: `/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/desktop-final.png`
- Mobile transcript snapshot: `/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/mobile-final.yml`
- Browser network log: `/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/network-final.log`
- Browser console log: `/Users/rajeev/Code/tools/local-llm-lab/output/playwright/agent-offload-role-proof-20260322/console-final.log`
- Final browser snapshot source: `/Users/rajeev/.playwright-cli/page-2026-03-22T02-08-57-279Z.yml`

## Notes

- The working Open WebUI approach is an exact-id override on the role model itself, for example `local-helper-fast:latest`, not a parallel preset id. That lets Open WebUI apply `think=false` while keeping the same selector entry.
- Open WebUI still logs two existing `tiptap` warnings in the console, but there were no browser errors during the verified flow.
- The raw `gpt-oss:20b` reasoning fallback remains opt-in. It can be cleaned up with `think=low`, but unlike Qwen 3.5 it still exposes a reasoning channel by design.
