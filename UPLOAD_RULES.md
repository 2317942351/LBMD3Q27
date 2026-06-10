# Upload Rules

These rules are fixed for this repository unless changed by an explicit owner
decision.

## Repository Visibility

The repository is public for third-party audit.

Public visibility means reviewers can inspect, fork, and comment according to
GitHub and applicable open-source license terms. It does not mean they can push
to this canonical repository. Direct write access is owner-only.

## Allowed

- Minimal TCLB model source snapshots needed for review.
- Diffs/patches against the upstream TCLB model source.
- Case XML files, manifests, and case-generation scripts.
- Postprocessing and audit scripts.
- Curated CSV/JSON/PNG/XML/log evidence.
- Public reference metadata and author-provided or extracted numerical data.
- Project audit notes and reproducibility instructions.

## Forbidden

- Raw simulation field outputs: `*.vti`, `*.pvti`, `*.pri`.
- GPU/CPU binaries and build products: `main`, `*.exe`, `*.dll`, `*.so`,
  `*.o`, `*.obj`, `CLB/`, generated object trees, and caches.
- Credentials, API tokens, SSH keys, cookies, `.env`, credential-manager
  dumps, and private machine configuration.
- Copyrighted article PDFs or HTML full text unless a later explicit legal
  review allows public redistribution.
- Opaque result archives: `*.tar`, `*.tgz`, `*.tar.gz`, `*.zip`, `*.7z`.
- Raw temporary folders, local virtual environments, and unreviewed generated
  scratch files.
- Any numerical shortcut that hides failure: clipping, unreported damping,
  pressure shifts, force cancellation, selective frame choice, or
  cherry-picked samples.

## Required Metadata

Every uploaded simulation artifact must identify:

- status label, normally `exploratory_not_validation`;
- source lane and upstream TCLB commit;
- binary SHA if the run used a compiled binary, recorded as metadata only;
- case geometry, lattice size, contact-angle convention, `M`, `IntWidth`,
  density/viscosity settings, and run length;
- postprocessing script and metric definitions;
- raw-output location if raw fields are retained outside the repository;
- nonfinite/failcheck result;
- mass drift and Mach report when available.

## Public Literature Boundary

For public GitHub use, include:

- DOI/title/metadata;
- manually extracted tables;
- author-supplied raw numerical data when redistribution is allowed;
- our analysis notes and provenance.

Do not include:

- publisher PDFs;
- publisher HTML full text;
- screenshots of copyrighted paper pages except where a separate fair-use/legal
  decision is made for a specific figure.

## Branch And Contribution Rules

- Keep `main` as the canonical branch.
- Do not grant write access to external reviewers.
- Do not accept unsolicited pull requests.
- Use issues or external review notes for comments and suggested fixes.
- Any accepted owner-side change must pass the audit checklist in
  `tools/public_repo_audit.ps1`.
