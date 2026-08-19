# Third-party notices and license inventory

Last audited: **2026-08-19 AEST**

iPromise uses open-source dependencies and hosted services. Their authors retain
their respective copyrights and licenses. The exact resolved dependency
inventories are:

- `pnpm-lock.yaml` for workspace development and release verification;
- `apps/console/pnpm-lock.yaml` for the console container;
- `apps/demo_saas/uv.lock` for the synthetic SaaS container; and
- `services/agent/uv.lock` for the agent container.

Notable direct dependencies include Next.js, React, FastAPI, Google Agent
Development Kit, Google Gen AI SDK, Google Cloud client libraries, PyJWT,
Pydantic, and Uvicorn. Build and test automation also uses GitHub Actions pinned
by commit SHA. Upstream package archives provide their license, copyright, and
NOTICE files; the lockfiles above are the source of truth for exact versions.

## License review

The locked graphs are predominantly permissive (MIT, ISC, Apache-2.0, BSD,
PSF-2.0, Python-2.0, BlueOak-1.0.0, 0BSD, and MIT-0). The audit identified these
additional obligations; none relicenses original iPromise code:

| License | Dependency and use | Release handling |
| --- | --- | --- |
| LGPL-3.0-or-later | The platform-specific `libvips` package used dynamically by Sharp in the Next.js runtime | Keep the LGPL notice and license with any distributed console binary or container, preserve users' LGPL rights, and provide the corresponding-source/relinking information required by that license. Recheck the target-platform package because the lock resolves platform-specific variants. |
| MPL-2.0 | `certifi` in the Python runtime; `axe-core` and `lightningcss` in development/build tooling | These are unmodified upstream files. Preserve their MPL notices and source availability if those files are redistributed. |
| CC-BY-4.0 | `caniuse-lite` browser-compatibility data | Preserve upstream attribution when redistributing the data. |
| CC0-1.0 | MDN and language-subtag development data | No attribution is required, but upstream provenance remains in package metadata. |

No AGPL, GPL-only, SSPL, BUSL, other strong network-copyleft/source-available
license, or unlicensed third-party package was detected in the installed graphs
checked against these locks. Dependencies are consumed as unmodified packages;
no upstream source tree is vendored in this repository. This is a release audit,
not a blanket legal opinion. Regenerate the inventory whenever a lockfile,
container target, or dependency changes.

Those dependencies are not relicensed by this notice. Anyone redistributing the
application must include the applicable upstream LICENSE, NOTICE, and copyright
files, including in standalone containers or browser bundles where required.
The Dockerfiles also pin official Node/Alpine and Python/Debian base images by
digest; anyone publishing a container image must inventory and preserve the
notices for the operating-system packages in that exact image. Google Cloud,
Vertex AI, Gemini, GitHub, and Devpost are third-party services governed by their
own terms; their names and marks remain the property of their owners.

The final demo narration uses Google Cloud Text-to-Speech voice
`en-AU-Neural2-C` to render an original entrant-authored script. Google's
[Text-to-Speech documentation](https://docs.cloud.google.com/text-to-speech/docs/basics)
permits generated audio in media including videos and recordings, subject to the
Google Cloud terms and applicable law. This narration service is submission
production tooling, not an additional AI model integrated into the product.

The cover graphic and architecture diagram in `docs/assets/` are original project
assets. The synthetic privacy page, records, and test identities are original
fixtures and contain no real customer data.

No project-level open-source license has been granted. Unless the repository owner
later publishes an explicit license, original iPromise code and assets are
all-rights-reserved. This statement does not restrict rights already granted by
the licenses of third-party components.
