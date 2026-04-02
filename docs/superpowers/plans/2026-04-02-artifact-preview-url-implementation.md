# Artifact Preview URL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a storage-agnostic `preview_url` contract so screenshot previews render with browser-native image URLs on local storage now and presigned/CDN URLs later.

**Architecture:** The backend storage layer will expose preview URLs. Local storage will use app-signed preview links served by a dedicated preview endpoint, while response mappers will embed `preview_url` into artifact payloads. The frontend will render screenshots from `previewUrl` instead of the authenticated content route.

**Tech Stack:** FastAPI, Pydantic, existing storage service, React, TypeScript, Vitest

---

### Task 1: Add backend preview signing helpers and storage contract

**Files:**
- Modify: `backend/app/core/config.py`
- Modify: `backend/app/storage/storage_service.py`
- Create: `backend/tests/test_storage_preview_urls.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_local_storage_preview_url_contains_signature_and_expiry():
    settings = Settings(
        storage_backend="local",
        preview_url_signing_secret="secret",
        preview_url_ttl_seconds=600,
    )
    service = StorageService(backend=LocalStorageBackend(settings))
    artifact = SimpleNamespace(
        id="artifact-1",
        name="step.png",
        storage_path="C:/tmp/step.png",
        content_type="image/png",
    )

    result = service.build_preview_descriptor(artifact)

    assert "/api/uploads/artifacts/artifact-1/preview" in result.url
    assert "expires=" in result.url
    assert "sig=" in result.url
    assert result.expires_at is not None
```

```python
def test_object_storage_preview_url_uses_presigned_backend_result():
    class FakeObjectBackend:
        def build_preview_descriptor(self, artifact, settings):
            return PreviewDescriptor(url="https://cdn.example.com/preview.png", expires_at="2030-01-01T00:00:00Z")

    service = StorageService(backend=FakeObjectBackend())
    artifact = SimpleNamespace(id="artifact-2", name="step.png", storage_path="s3://bucket/key", content_type="image/png")

    result = service.build_preview_descriptor(artifact)

    assert result.url == "https://cdn.example.com/preview.png"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_storage_preview_urls.py -v`
Expected: FAIL because preview descriptor support does not exist yet.

- [ ] **Step 3: Write minimal implementation**

Add:

```python
class PreviewDescriptor(NamedTuple):
    url: str
    expires_at: datetime | None
```

and:

```python
def build_preview_descriptor(self, artifact: ArtifactModel) -> PreviewDescriptor:
    return self.backend.build_preview_descriptor(artifact=artifact, settings=self.settings)
```

with local signing helpers and new settings:

```python
preview_url_signing_secret: str = "local-preview-secret"
preview_url_ttl_seconds: int = 900
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_storage_preview_urls.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/core/config.py backend/app/storage/storage_service.py backend/tests/test_storage_preview_urls.py
git commit -m "Add artifact preview URL storage contract"
```

### Task 2: Add local signed preview endpoint

**Files:**
- Modify: `backend/app/api/routes/uploads.py`
- Create: `backend/tests/test_artifact_preview_route.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_preview_route_serves_signed_local_artifact(client, db_session, user, artifact):
    url = storage_service.build_preview_descriptor(artifact).url

    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
```

```python
def test_preview_route_rejects_invalid_signature(client, artifact):
    response = client.get(f"/api/uploads/artifacts/{artifact.id}/preview?expires=9999999999&sig=bad")
    assert response.status_code == 403
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_artifact_preview_route.py -v`
Expected: FAIL because the preview route does not exist.

- [ ] **Step 3: Write minimal implementation**

Add a route:

```python
@router.get("/artifacts/{artifact_id}/preview")
def get_artifact_preview(...):
    storage_service.validate_preview_signature(...)
    artifact = db.get(ArtifactModel, artifact_id)
    ...
```

Serve local previews using the existing internal path optimization when available, otherwise stream bytes.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_artifact_preview_route.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/routes/uploads.py backend/tests/test_artifact_preview_route.py
git commit -m "Add signed artifact preview route"
```

### Task 3: Expose preview URLs in backend responses

**Files:**
- Modify: `backend/app/schemas/draft_session.py`
- Modify: `backend/app/services/mappers.py`
- Create: `backend/tests/test_artifact_preview_mapping.py`

- [ ] **Step 1: Write the failing tests**

```python
def test_map_step_screenshot_includes_preview_url():
    response = map_step_screenshot(step_screenshot)
    assert response.artifact.preview_url.endswith("/preview?expires=...")
```

```python
def test_map_candidate_screenshot_includes_preview_url():
    response = map_candidate_screenshot(candidate_screenshot, set())
    assert response.artifact.preview_url
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest backend/tests/test_artifact_preview_mapping.py -v`
Expected: FAIL because artifact responses do not include preview metadata.

- [ ] **Step 3: Write minimal implementation**

Extend `ArtifactResponse`:

```python
preview_url: str | None = None
preview_expires_at: datetime | None = None
```

Update mapper helpers to inject the preview descriptor into nested artifact payloads.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest backend/tests/test_artifact_preview_mapping.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/draft_session.py backend/app/services/mappers.py backend/tests/test_artifact_preview_mapping.py
git commit -m "Expose artifact preview URLs in session responses"
```

### Task 4: Update frontend contracts and screenshot rendering

**Files:**
- Modify: `frontend/src/types/process.ts`
- Modify: `frontend/src/types/session.ts`
- Modify: `frontend/src/services/contracts.ts`
- Modify: `frontend/src/services/mappers.ts`
- Modify: `frontend/src/components/common/AuthenticatedArtifactImage.tsx`
- Modify: `frontend/src/components/review/StepReviewPanel.tsx`
- Create: `frontend/src/components/common/AuthenticatedArtifactImage.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
it("renders screenshot previews from previewUrl", () => {
  render(<AuthenticatedArtifactImage artifactId="artifact-1" previewUrl="http://localhost:8000/api/uploads/artifacts/artifact-1/preview?sig=ok" alt="Step screenshot" />);

  expect(screen.getByRole("img", { name: "Step screenshot" })).toHaveAttribute(
    "src",
    "http://localhost:8000/api/uploads/artifacts/artifact-1/preview?sig=ok",
  );
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm run test -- src/components/common/AuthenticatedArtifactImage.test.tsx`
Expected: FAIL because the component does not accept `previewUrl`.

- [ ] **Step 3: Write minimal implementation**

Use:

```tsx
type AuthenticatedArtifactImageProps = {
  artifactId: string;
  previewUrl?: string | null;
  alt: string;
  className?: string;
};
```

and:

```tsx
const imageUrl = previewUrl ?? artifactService.getArtifactContentUrl(artifactId);
```

Map backend `preview_url` into frontend `previewUrl` for step screenshots and candidate screenshots.

- [ ] **Step 4: Run test to verify it passes**

Run: `npm run test -- src/components/common/AuthenticatedArtifactImage.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/process.ts frontend/src/types/session.ts frontend/src/services/contracts.ts frontend/src/services/mappers.ts frontend/src/components/common/AuthenticatedArtifactImage.tsx frontend/src/components/review/StepReviewPanel.tsx frontend/src/components/common/AuthenticatedArtifactImage.test.tsx
git commit -m "Render screenshots from preview URLs"
```

### Task 5: Verify end-to-end behavior

**Files:**
- No code changes required unless verification reveals a gap

- [ ] **Step 1: Run backend preview tests**

Run: `python -m pytest backend/tests/test_storage_preview_urls.py backend/tests/test_artifact_preview_route.py backend/tests/test_artifact_preview_mapping.py -v`
Expected: PASS

- [ ] **Step 2: Run frontend screenshot test**

Run: `npm run test -- src/components/common/AuthenticatedArtifactImage.test.tsx`
Expected: PASS

- [ ] **Step 3: Run frontend build**

Run: `npm run build`
Expected: PASS

- [ ] **Step 4: Manual QA**

Check:
- generate screenshots for a session
- reload the Process tab
- verify screenshot network requests hit `/preview`
- verify images render without `Image unavailable.`

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "Add storage-agnostic artifact preview URLs"
```
