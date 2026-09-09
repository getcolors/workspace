# Colors compute implementation plan

Started 2026-09-09. The five revised standards in `../standards/` are the
target contract, not evidence that existing packages conform.

## 1. Library structure and executable contract

- Create `getcolors/colors-compute` on `main`, with Green, Red, and Blue
  implementations, dependency exports, immutable release pins, and CI.
- Define provider-independent node requests, shared-resource references,
  remote backend configuration, normalized node results, and cluster joins.
- Implement topology expansion, stable state identities, validation, and
  fail-closed state decisions with common fixtures and cross-color parity.
- Keep provider behavior in the library and application behavior in packages.

## 2. Providers, backends, and shared lifecycle

- Implement Azure, AWS, Google, DigitalOcean, hcloud, Vultr, Yandex, and OCI.
- Implement R2 and S3 remote state, preserving AWS compute's ambient credential
  chain when R2 is selected. Refuse `no-infra` and unsupported selections.
- Prepare deployment SSH keys and shared networks once, then execute node
  operations through the matching Colors SDK.
- Persist ownership before dispatch; serialize competing deployment runs;
  preserve recovery information on partial failure and scale-down.
- Check deterministic render parity, meaningful lifecycle tests, provider
  schemas, backend combinations, and keygen/opt-out behavior. Render checks
  alone do not establish live deployment support.

## 3. Cluster packages first

- Inventory AutoMQ, Langfuse, MySQL HA/AGY, PostgreSQL HA/AGY, Kubernetes machine
  packages, ClickHouse, and any additional machine-creating cluster consumers.
- Begin with AutoMQ as the homogeneous cluster proof, then cover role-based
  topology before migrating the remaining cluster packages.
- Replace package-owned compute with Colors fan-out calling the same library
  node operation, followed by a complete result collector for Ansible.
- Preserve application semantics, shared-resource ownership, aliases, and SSH
  access. Update dependency manifests, lockfiles, bundled skill launchers,
  package documentation, tests, and desired-state examples together.
- Before changing live ownership, record state backups, resource mappings,
  transfer/recovery procedures, and plans that show no unintended replacement.
- Use isolated live deployments only when needed for evidence. Record their
  identity, resources, validation, and cleanup in the handoff. Do not silently
  repurpose an existing production deployment for a test.

## 4. Version-only adoption proof, then single-host packages

- Add a fixture provider inside the library and prove an existing cluster
  consumer supports it with dependency changes alone.
- After cluster migrations, migrate a single-host consumer to the identical
  node operation and repeat the version-only proof.
- Migrate every remaining compute-creating single-host package. No package
  provider registry, template, or provider-specific application branch remains.
- Keep local SSH config plays package-owned and driven by normalized results.

## 5. Publish, validate, and complete rollout

- Commit and push standards and plan to `workspace/main`, without including
  unrelated pre-existing changes.
- Commit and push library code to `colors-compute/main` before pinning consumer
  dependencies. Push package implementations before stamping launcher pins.
- Run each affected repository's required checks and inspect golden diffs.
  Do not claim support for providers or migrations whose checks did not run.
- Update installed deployment launchers only after package migration evidence
  is complete. Keep Green, Red, and Blue state-compatible.
- Before every stop, update `colors-compute-handoff.md` with commits, tests,
  remaining work, blockers, and any live resources. Completion requires the
  full rollout; foundation commits alone do not complete this plan.

## Authorization and working-tree boundaries

The user authorized implementation, subagents, commits and pushes to `main`,
and live deployments if needed. No repeated approval is required for that work.
At start, `workspace/scripts/package-copies.py`, `workspace/card-prompt.md`,
and `workspace/scripts/__pycache__/` had unrelated changes. Preserve them and
exclude them from this task's commits unless later work requires a reviewed
change to the same file. The five standards were revised in this conversation.

## Progress

- [x] Revise the five standards.
- [x] Record the plan and authorization.
- [x] Publish standards and plan, workspace `873f384`.
- [x] Publish tested contract/SDK workflow foundation, colors-compute `a112e17`.
- [x] Publish private state readers and pure coordination transitions, colors-compute `fba3e4c`.
- [x] Publish conditional journal transport and native HTTPS contention probes, colors-compute `5ffa2a1`.
- [ ] Implement and publish the complete three-color lifecycle library.
- [ ] Migrate cluster package skills.
- [ ] Prove version-only provider adoption.
- [ ] Migrate single-host package skills.
- [ ] Validate and publish deployment migrations.
