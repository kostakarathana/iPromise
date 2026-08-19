# Third-party notices and license inventory

iPromise uses open-source dependencies and hosted services. Their authors retain
their respective copyrights and licenses. The authoritative dependency inventory
is the repository's locked manifests: `pnpm-lock.yaml`,
`apps/demo_saas/uv.lock`, and `services/agent/uv.lock`. Notable direct dependencies
include Next.js, React, FastAPI, Google Agent Development Kit, Google Gen AI SDK,
Google Cloud client libraries, PyJWT, Pydantic, and Uvicorn. Build and test
automation also uses GitHub Actions pinned by commit SHA.

Those dependencies are not relicensed by this notice. Anyone redistributing the
application must review the exact locked versions and comply with each upstream
license and notice. Google Cloud, Vertex AI, Gemini, GitHub, and Devpost are
third-party services governed by their own terms; their names and marks remain the
property of their owners.

The cover graphic and architecture diagram in `docs/assets/` are original project
assets. The synthetic privacy page, records, and test identities are original
fixtures and contain no real customer data.

No project-level open-source license has been granted. Unless the repository owner
later publishes an explicit license, original iPromise code and assets are
all-rights-reserved. This statement does not restrict rights already granted by
the licenses of third-party components.
