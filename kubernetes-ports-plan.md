# Kubernetes SDK and Package Skill ports

Requested on 2026-09-16. Work uses the Linux checkouts under `/home/ubuntu/code/getcolors`, which correspond to the supplied macOS paths.

## Plan

1. Sync each affected checkout with main before work. Preserve existing edits and inspect existing ports before replacing anything. Read repository instructions and apply the requested unslop skill to new prose.
2. Audit Red and Blue Kubernetes SDK implementations against Green. Complete controller and client behavior, add regression coverage, run native suites and publish SDK changes before downstream pin updates.
3. Complete DOKS in all three colours with native workflows, matching validation and lifecycle behavior, standalone Package Skills, fixture parity and package website documentation.
4. Complete Redis operator Red and Blue controllers and Package Skills. Preserve suspension, deletion, ownership, recovery, credential and restart guarantees. Add native tests, rendering parity, launcher checks and controller image support. Update its website and instructions.
5. Run offline checks before live operations. Reuse credentials from sibling deployment repositories only through ignored secret files or process environments. Never print or commit secrets. Use the existing DOKS platform where possible, preserve state ownership and test each colour against live Kubernetes and Redis. Record exact evidence and failures. Avoid deleting shared infrastructure; remove only dedicated test resources.
6. Commit and push reviewed changes to main in dependency order. Stamp package pins with repository tooling, install payloads in affected deployments, compare copied launchers and validate published launchers. Update workspace inventory where descriptions change.
7. Write a handoff file as the final work step with commits, checks, live evidence, remaining resources and any unresolved limitations. Share its link.

## Assignment

The primary agent owns integration, live deployment checks, dependency sequencing, workspace documentation and the final handoff. Separate agents own the SDK audit, DOKS completion and Redis operator completion. Each agent must read its repository instructions, preserve existing work and report test results.

## Initial state

Green, Red, Blue, DOKS, Redis operator, workspace and both deployment checkouts were fetched and synchronized. DOKS required disabling pull.rebase for its fast-forward check because three launcher files already had edits. Red and Blue Kubernetes modules and DOKS ports already exist. Redis operator contains untracked partial Red and Blue implementations. These are inputs to review and complete.

## Website catalog follow-up

Update the main website recipes and featured copy to list Green, Red and Blue for DOKS and Redis Operator. Refresh these packages' discovery pins from their published main branches, regenerate skill bundles and social cards, and run the website checks. Push main, verify the production deployment and all six skill routes, then record the correction in the handoff.
