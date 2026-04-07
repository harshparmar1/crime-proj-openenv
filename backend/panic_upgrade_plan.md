# Panic System Upgrade Plan

## Scope
Upgrade existing panic button into a production-grade intelligent emergency system across React/Tailwind frontend, FastAPI backend, and WebSocket real-time pipeline. Preserve current flows and extend them.

## Current Baseline (Key Files)
- Frontend panic button: frontend/src/components/intelligence/PanicFab.jsx
- Panic UI entry: frontend/src/pages/DashboardPage.jsx
- Police alerts UI: frontend/src/pages/PoliceDashboard.jsx
- Realtime hook: frontend/src/hooks/useCrimeSocket.js
- Panic API: backend/app/routers/panic_routes.py
- WebSocket hub: backend/app/services/ws_hub.py
- Realtime WS route: backend/app/routers/realtime_routes.py
- Notifications: backend/app/services/notify_service.py
- DB models: backend/app/db.py

## Phase 1: Backend Foundation
1. **Panic session model**
   - Add new table `panic_sessions` with `session_id`, `user_email`, `start_time`, `status`, `priority`, `risk_score`, `last_lat`, `last_lng`.
   - Add `panic_events` or `panic_tracks` table for tracking history (lat, lng, ts, session_id).
2. **Session APIs**
   - POST `/panic/start` to create session, save snapshot/video metadata, return `session_id` and initial status steps.
   - POST `/panic/track` to append location updates.
   - POST `/panic/stop` to end session.
3. **Priority engine**
   - Add helper in a new service (e.g., `panic_service.py`) to set priority: panic=HIGH, normal=MEDIUM.
4. **Realtime broadcast**
   - Broadcast panic session updates via `hub.broadcast` with event types: `panic_session`, `panic_track`, `panic_status`.
5. **Response simulation**
   - Add async background task for simulated status changes (police assigned -> dispatched -> arriving).
6. **Security**
   - Rate limit panic start (5 sec rule) using a simple in-memory cache keyed by user or a DB timestamp check.
   - Validate payloads, reject invalid lat/lng, and enforce auth.

## Phase 2: AI Intelligence Layer
1. **Risk scoring**
   - Use existing `predict_service.py` to calculate risk level for panic (state/region/time + recent count).
   - Expose in panic response and store on session.
2. **Smart alert message**
   - Generate message on backend and include in WS payload + notifications.
3. **Anomaly detection**
   - Check for frequent panic triggers from same user; flag and include a `suspicious` flag.

## Phase 3: Frontend Emergency UX
1. **Emergency mode UI**
   - Create overlay component (full-screen red, pulsing, countdown, status steps).
   - Trigger on panic start and keep until session end.
2. **Multi-tap / hold trigger**
   - Require double-tap or 2-second hold in PanicFab.
3. **Live tracking + stop**
   - Send location every 10s while active.
   - Provide stop button in emergency overlay.
4. **Audio + visual alert**
   - Play alarm sound and flash effect (use audio file asset).
5. **Offline queue**
   - Queue panic start and tracking updates in localStorage; auto-send when back online.
6. **Auto video recording**
   - Capture 5-10 seconds video, upload to `/panic/start`.
7. **Smart status tracker**
   - Show status steps synced from backend via WS.

## Phase 4: Police Dashboard Integration
1. **Priority highlight**
   - Render panic alerts at top with red blinking badge.
2. **Live location tracking**
   - Show moving marker and last update time.
3. **Quick actions**
   - Buttons: assign officer, dispatch, resolve.
   - API integration: `/panic/{session_id}/status`.

## Detailed Implementation Steps
1. **DB**: add `PanicSession` and `PanicTrack` models in backend/app/db.py.
2. **Services**: create backend/app/services/panic_service.py for priority, risk score, session status updates.
3. **Routes**: new router backend/app/routers/panic_session_routes.py.
4. **WebSocket**: extend hub broadcast payloads in panic routes.
5. **Frontend**: create new components in frontend/src/components/intelligence/:
   - `EmergencyOverlay.jsx`
   - `PanicTracker.jsx`
   - `EmergencyStatusSteps.jsx`
6. **Frontend hooks**: add `usePanicSession.js` for handling tracking, offline queue, websocket updates.
7. **Police Dashboard**: update alerts stream and render live panic sessions.

## Edge Case Handling
- No GPS -> fallback to manual location input.
- No camera -> skip media upload gracefully.
- Offline -> local queue and auto-resend on online.

## Verification
- Start backend and frontend.
- Trigger panic and validate:
  - Session created and broadcast received.
  - Live tracking sends updates every 10s.
  - Emergency overlay shows countdown and status progression.
  - Offline mode queues and auto-sends when online.
  - Police dashboard shows live location and status updates.
- Run manual tests: double-tap/hold trigger, video recording permission denied, GPS denied.
