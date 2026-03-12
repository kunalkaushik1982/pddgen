# Storage Migration Notes

The current pilot uses local filesystem storage. The system should be able to move later to:

- shared internal storage
- SharePoint-style repository integration
- S3-compatible object storage

## Migration Principle

Application code should depend on storage capabilities, not storage location.

Required capabilities:

- save uploaded file
- save generated binary output
- read text transcript
- resolve stored artifact path or identifier

## Migration Considerations

### Shared Internal Storage

Pros:

- familiar in enterprise environments
- easy handoff to internal teams

Cons:

- weaker portability
- operational coupling to shared filesystem access

### SharePoint-style Storage

Pros:

- strong enterprise fit for document-centric workflows
- aligns with documentation repositories

Cons:

- API and permission complexity
- not ideal as the first raw processing store for large media files

### S3-Compatible Object Storage

Pros:

- strong scalability model
- clean separation between app and storage

Cons:

- requires object-store provisioning and access management

## Recommended Path

- pilot: local filesystem
- early internal rollout: shared storage or object storage depending on enterprise readiness
- document repository handoff can later be separate from raw processing storage
