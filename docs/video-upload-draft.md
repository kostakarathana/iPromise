# Public video upload draft

Status: **prepared, not uploaded**

## Title

iPromise — Customer promises should behave like tests | All Things Agentic Hackathon

## Description

iPromise is a Taskmaster agent that turns a supported customer promise into a
recurring executable control, tests an entrant-owned synthetic product, and
opens a verified draft pull request when observed behavior drifts from the
promise.

This submission uses Gemini 3.5 Flash through Vertex AI, Google Agent
Development Kit (ADK), Cloud Run, Firestore, Cloud Scheduler, Secret Manager,
Cloud Logging, Cloud Build, and a least-privilege GitHub App.

The recorded workflow tests one scoped account-deletion promise against
synthetic application and analytics records. The live segment is a distinct
duplicate occurrence that executes the complete workflow and safely reconciles
to the existing verified draft PR. The earlier creator run, matching Cloud Build
receipt, exact PR diff, and Cloud Run deployment are shown separately. iPromise
does not make a legal-compliance conclusion, merge code, deploy code, or use real
customer data.

English narration was synthesized from the entrant-authored script with Google
Cloud Text-to-Speech voice `en-AU-Neural2-C`. It is production tooling for this
video, not an additional model used by the iPromise product.

Repository: https://github.com/kostakarathana/iPromise
Hosted project: https://ipromise-console-ipj6vqlg2q-uc.a.run.app

This video was created to enter Google's All Things Agentic Hackathon.

#AllThingsAgenticHackathon

## Upload settings

- Visibility: **Public**
- Audience: **No, it is not made for kids**
- Category: **Science & Technology**
- Language: **English**
- Thumbnail: `docs/assets/ipromise-video-thumbnail.png` (1920×1080, derived
  mechanically from the original cover without the burned caption layer)
- Local master: `artifacts/video/browser-native/ipromise-hackathon-demo-final.mp4`
- Burned captions: already present; upload `artifacts/video/browser-native/captions.srt`
  as a separate English caption track too if the platform accepts it
- Do not enable automatic chapters if they obscure the first four-minute proof
- Do not trim, enhance, stabilize, or replace audio in the platform editor

## Post-upload release gate

1. Wait for 1080p processing to complete.
2. Confirm duration is 3:30 and playback starts without sign-in.
3. Test the public URL in a logged-out browser at 1080p with sound and captions.
4. Confirm the source, synthetic-data disclosure, run IDs, Cloud Build, PR, Cloud
   Run page, and architecture remain legible.
5. Record the final URL and platform video ID in
   `docs/submission-release.md`, `docs/devpost-submission-draft.md`, and the
   evidence matrix before creating the immutable submission tag.
6. Keep the public video unchanged through judging.
