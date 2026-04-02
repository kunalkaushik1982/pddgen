# Artifact Preview URL Design

## Goal

Replace brittle authenticated image-tag loading with a storage-agnostic `preview_url` contract so screenshot previews render through browser-native `<img src>` paths on local storage today and presigned or CDN-backed URLs later.

## Problem

The current screenshot preview path renders images with:

- `GET /api/uploads/artifacts/{artifact_id}/content`
- raw `<img src="...">`

This route is authenticated with the user session. In the current environment:

- screenshot files are generated correctly
- session payloads include screenshot metadata correctly
- direct authenticated `fetch(..., { credentials: "include" })` succeeds
- raw browser image loading fails and the UI falls back to `Image unavailable.`

The failure boundary is the browser image request, not screenshot generation or persistence.

## Desired Outcome

The frontend should render screenshots from a plain `preview_url` and should not need to know:

- whether storage is local or object-backed
- whether auth is cookie-based
- whether preview delivery comes from the app, object storage, or a CDN

The backend should decide how to produce the preview URL.

## Architecture

### 1. Storage-level preview contract

Add a preview URL abstraction to the storage layer. The backend should be able to ask for a preview URL for an artifact and receive a result like:

- `url`
- `expires_at`

This abstraction will have different implementations per backend:

- local storage: app-signed temporary preview URLs
- S3 or R2: provider presigned URLs
- future CDN: signed CDN URLs

### 2. Dedicated preview route for local storage

Keep the current authenticated content route for downloads and internal access:

- `/api/uploads/artifacts/{artifact_id}/content`

Add a new preview route for local signed access:

- `/api/uploads/artifacts/{artifact_id}/preview`

Local preview requests should be authorized by signed query parameters rather than user session cookies. The route should validate:

- signature
- expiry
- artifact existence

Then it should serve the preview efficiently using the existing storage service and nginx internal path support when available.

### 3. API response contract

Artifacts that can be previewed in the UI should include:

- `preview_url`
- `preview_expires_at`

This should be added to:

- `ArtifactResponse`
- step screenshot payloads
- candidate screenshot payloads
- session detail responses that already embed these artifacts

### 4. Frontend rendering contract

Frontend preview rendering should prefer:

- `previewUrl`

and treat it as a normal image URL. The frontend should not need authenticated blob loading for the default path.

This restores performant browser-native rendering while keeping the storage implementation flexible.

## Security Model

### Local storage

Preview URLs should be short-lived and signed by the application using a dedicated signing secret and expiry window. The signed URL itself becomes the authorization for preview access.

This avoids depending on cookies in browser image requests.

### Cloud storage

When the storage backend is object-backed, the storage service should return provider-native presigned URLs or CDN-signed URLs. The frontend contract does not change.

## Backward Compatibility

Do not remove the existing authenticated content route in this change.

The rollout should:

1. add preview URL support
2. expose `preview_url` in responses
3. update frontend preview rendering to use `preview_url`
4. keep the old content route available for non-preview use cases

## Testing Strategy

### Backend

- preview URL signing and validation tests
- preview route success and failure tests
- response mapping tests to ensure screenshot artifacts include `preview_url`

### Frontend

- mapper tests for `preview_url`
- screenshot preview rendering test asserting the component uses `previewUrl`

### Manual

- generate screenshots locally
- reload session detail page
- verify Process tab images render through `preview_url`

## Non-Goals

- removing the existing content route
- redesigning artifact download behavior
- introducing CDN infrastructure in this branch
- changing screenshot generation logic
