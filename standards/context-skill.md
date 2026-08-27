# Context Skill Standard

Status: normative. Reference implementation: `skills/agent-network-single-node`.
Consumers: `skills/create-context-skill` (the distillation workflow),
`skills/submit-context-skill` (catalog admission), and the `colors-website`
catalog validation.

This document defines what a Context Skill is, what it must carry, and what it
must not. It exists because the category otherwise exists only by example:
three skills named `*-single-node` share a shape no document describes, two of
them carry working files the third deliberately refuses, and nothing separates
a Context Skill from a well-written README except taste.

## 1. Definition

A **Context Skill** is distilled knowledge from a verified build: the traps,
contracts, and acceptance doctrine that separate a stack that runs from a
deployment whose claims are proven. It is the third kind of skill in this
ecosystem, beside the other two:

| | Generic skill | Package Skill | Context Skill |
|---|---|---|---|
| The agent gets | a procedure | a product to converge | knowledge to reason with |
| Routed by | task intent | desired state (`colors.yml`) | symptoms |
| Installed by | `npx skills use` | `npx skills add`, SHA-pinned | `npx skills use` |
| Ships | instructions ± a script | launcher + tested templates | claims + provenance |

A Context Skill MUST be knowledge bought from a build that was verified against
the real platform. General documentation, tutorials, prompt libraries, and
summaries of upstream docs do not qualify, however well written: their claims
were not paid for, and the category dies of dilution if they are admitted.

## 2. The five required artifacts

A conforming Context Skill MUST carry all five. They are the checkable residue
of verification — an admission validator cannot re-run the build, so it
verifies what the build left behind.

1. **A symptom-first routing `description`** — error strings, observed
   behaviours, and situations, not mechanism. It is the only text an agent
   reads when deciding to load the skill, and it MUST satisfy the Agent Skills
   specification: 1–1024 characters. When the symptom index exceeds the cap,
   the highest-signal symptoms stay in the description and the full index
   moves to the top of the body.
2. **Provenance statements in the body.** The skill states what its claims
   were verified against ("verified against a running deployment unless it
   says otherwise"), and where it contradicts upstream documentation it names
   the source function it read instead of the sentence it rejected.
3. **A pinned version set** with the rules that generated it
   (`references/pins.md` or equivalent). Claims decay when pins move; undated
   claims cannot be re-verified.
4. **A symptom-indexed failure catalogue** with verbatim error text
   (`references/failure-catalogue.md` or equivalent), searchable by the string
   on the reader's screen.
5. **Evals shaped as a user in trouble** (`evals/`), written as the support
   message someone would actually send — testing routing and diagnosis
   together. Evals are the category's regression net, the analog of
   `bb golden`.

## 3. No second copy

The rule targets drift, not files. A Context Skill MUST NOT carry a copy of
anything a tested implementation owns.

- When a companion Package Skill exists (§4), `assets/` and working-file
  copies are disqualifying. The package repository is the single tested
  implementation; the Context Skill carries the *why*. This workspace has a
  documented history of the failure this prevents: a second, untested copy of
  a compose file drifts.
- A Context Skill for a domain with no companion MAY ship assets. The catalog
  recipe MUST flag them, and when a companion Package Skill later lands, the
  assets MUST migrate out before the next catalog update.

## 4. The companion link

A Context Skill SHOULD name its reference implementation — the repository
holding the tested working files — in its body, and its catalog recipe carries
that repository as `companion:`. The link renders in both directions: the
context page points at the product, the product page points at its context
companion. A Context Skill with no companion is legitimate (§3); a companion
that does not resolve is not.

## 5. Validation

`skills-ref validate` MUST pass: frontmatter shape, the `name` grammar, the
directory-name match, and the 1024-character description cap all come from the
Agent Skills specification, and the catalog does not admit what the ecosystem's
own validator rejects.

## 6. Decay and re-verification

A Context Skill's claims are true at its pinned versions and unknown after
them. On a pin bump the skill's own re-test instructions apply (the reference
implementation's ACME defect names its retest condition explicitly), evals are
re-run, and claims that no longer hold are corrected — never silently kept.
A Context Skill that stops being maintained SHOULD say so rather than let its
pins imply currency.

## 7. Adoption

`agent-network-single-node` defines the shape and conforms: its routing
description was trimmed to the 1024-character cap per §2.1 on 2026-08-27, with
the full symptom index at the top of the body. Both siblings migrated per §3
on 2026-08-27. `posthog-single-node`'s assets were byte-identical with the
`getcolors/posthog` tools tree and became pointers.
`rybbit-single-node`'s had all diverged — it carried the portable variant —
which is §3's argument made flesh: its one verified improvement (the UDP 443
HTTP/3 publication) was upstreamed to `getcolors/rybbit` before deletion,
and the rest of the drift was the package being ahead of the copy. Every
current Context Skill now conforms. Catalog admission is governed by
`submit-context-skill`, which cites this standard.
