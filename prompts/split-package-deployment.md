Split the deployment currently embedded in <PACKAGE_PATH> into its own repository at <DEPLOYMENT_PATH>, published as <ORG>/<DEPLOYMENT_REPO> with <PUBLIC_OR_PRIVATE> visibility.

Proceed with implementation, commits, and pushes. Use subagents for independent preparation and review.

Keep reusable implementation, tests, package metadata, CI, canonical skills, and generic examples in the package repository. Move deployment-specific configuration, copied immutable launchers, installed skills, environment tooling, and operational documentation into the deployment repository.

Preserve the existing launcher/dependency pins, configuration, profile, resource identities, and private authority. This is a local repository/directory relocation—not an upgrade, reprovisioning, or cloud migration. Do not create, converge, delete, or otherwise modify cloud resources.

Read applicable instructions and inspect Git status first. Preserve existing user changes. Never print secrets or private file contents.

For private deployment files:
- Identify the actual state, credentials, SSH authority, and recovery files.
- Save a consistent Vault checkpoint before relocation, reusing my unlocked session.
- Restore into the new directory using matching configuration.
- Preserve restrictive permissions and exclude private files, recovery output, and archives from Git.
- Prevent concurrent controller operations during relocation.
- Update only owned local SSH key/known-hosts paths, preserving addresses, users, and unrelated configuration. Validate locally; do not require cloud authentication for this.
- Save a checkpoint from the new directory, preserving existing Vault document/version history.
- Verify recovery, then archive old local deployment files outside both repositories. Leave only one active controller directory. Do not archive continued Vault documents or GitHub repositories.

Replace actual deployment configuration in the package with a synthetic example. Update documentation, links, and repository inventory. Review tracked files before publication; do not copy the package’s full Git history into the deployment repository.

Run relevant local validation and report repository URLs, commits, checks, active deployment path, private archive location, and checkpoint status. If cloud verification is unavailable, report that separately without blocking the local relocation. Ask only for genuinely missing information or an unavoidable external action.
