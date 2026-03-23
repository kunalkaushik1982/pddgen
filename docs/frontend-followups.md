# Frontend Follow-Ups

This is the deferred frontend work after the current refactor batch. The frontend is structurally in much better shape now; the items below are the remaining hardening and maturity work to revisit after backend cleanup.

## High priority

- [ ] Replace frontend bearer-token storage with secure cookie-based auth once backend supports it.
- [ ] Rework protected artifact access to align with the new backend auth/session model.
- [ ] Expand automated tests for:
  - [ ] auth route behavior
  - [ ] project retry/export flows
  - [ ] ask-session request lifecycle
  - [ ] session-detail integration flow
  - [ ] diagram editor interactions

## Medium priority

- [ ] Future artifact-delivery hardening:
  - [ ] object storage + signed URLs for cloud deployments
  - [ ] cache headers for immutable screenshots
  - [ ] artifact access audit logs if required
  - [ ] thumbnail support for large screenshot sets
  - [ ] lazy loading / intersection observer for screenshot-heavy views
  - [ ] short-lived signed URL expiry policy
  - [ ] ensure raw storage paths are never exposed publicly
- [ ] Run a full accessibility pass across all screens:
  - [ ] keyboard-only navigation
  - [ ] screen-reader labels and announcements
  - [ ] focus return on all dialogs and route transitions
  - [ ] accessible names for icon/text actions
- [ ] Improve route-level and feature-level error handling UX with clearer retry states.
- [ ] Refine loading states and skeletons for session detail and projects refresh.
- [ ] Improve Ask-this-Session UX:
  - [ ] suggested questions
  - [ ] better empty states
  - [ ] persisted chat history if required
- [ ] Polish diagram editor UX:
  - [ ] undo/redo feedback
  - [ ] node/connector action affordances
  - [ ] keyboard behavior validation
- [ ] Consider client-side error telemetry.

## Low to medium priority

- [ ] Move any remaining repeated UI strings into `frontend/src/constants/uiCopy.ts`.
- [ ] Move any remaining UI timings or feature flags into `frontend/src/config/appConfig.ts`.
- [ ] Formalize a light design-system layer for button, field, and panel variants.
- [ ] Further split heavy frontend chunks if bundle size becomes a real issue.

## Deferred external dependency cleanup

- [ ] Remove `frontend/src/react-jsx-compat.d.ts` once `@reactflow/*` becomes fully React-19-compatible.
