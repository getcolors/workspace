# Kubernetes ports handoff

Completed on 2026-09-16. The [plan](kubernetes-ports-plan.md) is implemented. All changes are committed and pushed to main.

## Delivered

Completed and verified the native Red and Blue Kubernetes SDKs, DOKS Package Skills, and Redis operator controllers and Package Skills. The operator supports build, create, check, rehearse, drill, restart and guarded delete in all three colours.

The work includes ownership-check corrections, matching validation, byte-for-byte rendering parity, standalone launchers, native controller images, cross-colour probe dispatch, and CI coverage. Successful malformed provider responses now fail instead of masquerading as confirmed Droplet absence. The Red image installs TypeScript dependencies on the build machine's native architecture before copying them into the amd64 image.

The [DOKS website](https://getcolors.github.io/doks/) and [Redis operator website](https://getcolors.github.io/redis-operator/) are updated and published. Both retain their analytics tags. Workspace inventory and GitHub repository metadata agree.

## Published revisions

| Repository | Main revision |
|---|---|
| Red SDK | [f22dc85](https://github.com/getcolors/red/commit/f22dc85c9f575e7cb16828f0980eed0456caf9f9) |
| Blue SDK | [9bcd828](https://github.com/getcolors/blue/commit/9bcd82890f04387256ba9a302d37eb30a638ae56) |
| DOKS package | [7d7c991](https://github.com/getcolors/doks/commit/7d7c99162f8186b5192e6acc8647c60f020d9d96) |
| Redis operator package | [bf5fd42](https://github.com/getcolors/redis-operator/commit/bf5fd4226f05f94d2f5752288a9bb65322f7dc5a) |
| DOKS deployment | [de1fe7d](https://github.com/getcolors/doks-dev/commit/de1fe7d03ad2291af48f9e7821b6ca2d1e2314a4) |
| Redis operator deployment | [c6467b1](https://github.com/getcolors/redis-operator-doks/commit/c6467b16a7c65b79471404e5a5eae3fc6a6d0945) |

DOKS launchers pin implementation `8120674e81d88827c4e8b6eaa899b0c5fbaf829c`. Redis operator launchers and final images use implementation `8251d68edef252902f32da68d4b46ec19e9a760f`. Later package commits stamp launchers or update documentation. Every copied deployment launcher matches its installed skill payload, and the installer maintains both lockfiles.

## Validation

| Component | Passed checks |
|---|---|
| Red SDK | 137 tests and type checking; two opt-in tests skipped |
| Blue SDK | 150 tests; two opt-in tests skipped |
| DOKS | Green 36 tests, Red 10 tests and type checking, Blue 10 tests, golden fixtures, provider parity, copied and cold launchers |
| Redis operator | Green 43 tests, Red 9 tests and type checking, Blue 32 tests, golden fixtures, byte parity including a custom namespace, copied and cold launchers |
| CI and websites | Latest package CI and Pages deployments passed |

Both SDKs passed actual Kubernetes API tests for status and finalizer writes, readiness, idempotence, stale-write rejection, stopped state, Retain and Destroy. Those SDK tests used in-memory infrastructure adapters. Their temporary namespace and CRD were removed.

Red created the previously absent DOKS development cluster and registry. Blue converged the same resources, and all three colours passed live checks. Blue refreshed the kubeconfig; Red obtained the registry push credential.

Both operator runtimes passed authenticated Redis health, fresh backup restoration and restart verification. Blue created the initial Redis Droplet. Red adopted the same Droplet. Green, Red and Blue CLIs all successfully probed the Red image.

Red's recovery drill replaced Droplet `601089393` with `601094147`. It verified old-resource absence, a different provider ID, unchanged custom-resource UID and generation, and an authenticated write after recovery. The first installation on the replacement hit Ubuntu's dpkg lock. The controller retained the masked failure and retried successfully without manual intervention. One historical failure log remains; the final resource is Ready.

The drill used synthetic data and proves service recovery, not automatic restoration of the deleted host's data. Both colours verified backup restoration separately. Live provider coverage was DigitalOcean. Vultr was covered by fixture parity. Package teardown was not run against the live deployments; deletion guards and SDK finalizer behavior were tested.

Evidence:

- [DOKS and SDK verification](https://github.com/getcolors/doks-dev/tree/main/evidence/2026-09-16)
- [Operator verification and per-colour records](https://github.com/getcolors/redis-operator-doks/tree/main/evidence/2026-09-16)

## Current running resources

| Resource | Current value |
|---|---|
| DOKS cluster | `doks-dev`, `be709b80-df9d-4bf0-8d6b-5333c650d9a6`, ams3 |
| Worker | `doks-dev-3f1o90`, `159.223.1.98` |
| Registry | `registry.digitalocean.com/doks-dev` |
| Namespace | `colors-redis` |
| Redis Droplet | `601094147`, `146.190.24.194` |
| RedisDeployment UID | `e92793d1-546f-4779-86a8-d0405649c755` |
| Final resource status | Ready, generation 5 observed, suspension false |
| Deployed controller | Red; zero pod restarts in the final snapshot |

The cluster, registry, persistent volume and Redis Droplet remain running. Destruction protection and Retain policy remain enabled. Temporary SDK and image-smoke resources were removed.

Final image digests:

- Red: `registry.digitalocean.com/doks-dev/redis-operator-red@sha256:8d53eb6932dddc3e9b512545ae02f7123f54acbc0d0d3346d7bd8331c21f3d8c`
- Blue: `registry.digitalocean.com/doks-dev/redis-operator-blue@sha256:5caa4c9df3e4e969895dfb8d68dac0372e144203d140de920fc9d9d578bd72ba`

The launcher selects the CLI implementation. The `image` value in `colors.yml` selects the controller runtime. All three installed CLIs can operate either final image.

Credentials were reused from sibling deployments' ignored `.envrc.private` files and supplied to the Kubernetes Secret through stdin. No credential values or Terraform state were committed. The kubeconfig remains generated under `doks-dev/.colors/doks-dev/kubeconfig`.

With each deployment's normal environment loaded, use `./red check` in `redis-operator-doks` and any colour's `check` in `doks-dev` to inspect the running services.

## Website catalog correction

The original implementation updated the package repository pages but missed the main website catalog. This is now corrected and deployed in `colors-website` commit `369cde28d71017b4b57f38e3e1c9f9fbda2632ff`.

Both https://www.getcolors.ai/getcolors/doks and https://www.getcolors.ai/getcolors/redis-operator list Green, Red and Blue. The featured page describes all three runtimes. Discovery pins and archives were regenerated from the published package commits, and the new routes have social cards.

Validation: `pnpm typecheck` passed with zero diagnostics; `pnpm build` produced 172 pages. All six live skill pages, both source pages, the featured runtime notes and all six downloadable archive SHA256 digests were verified. GitHub Actions run https://github.com/getcolors/colors-website/actions/runs/35118067601 completed successfully, including production deployment. Its first AMD64 attempt failed downloading BuildKit because Docker Hub reset the connection; the failed-job retry passed without code changes.
