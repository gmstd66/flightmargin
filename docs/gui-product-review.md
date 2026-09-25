# Windows GUI/product review

This is an owner-led review of the internal Windows desktop build at version
0.2.0. It is unsigned, not public, and must not be uploaded or released.
Record observations and decisions separately; this checklist deliberately does
not prescribe a redesign.

The current review build uses a compact 600×450 default window (560×400
minimum), a three-row schema-v3 dashboard, pointer-handle drag/snap, bounded
direct card resizing, panel visibility, and reset. All six default panels must
be visible without a scrollbar. The first owner review found stale stacked
assets, immovable quota gauges, resize spill, and a visible console; the review
build now revisions its local assets, keeps gauge cards at responsive minimums,
and builds the release shell as a Windows GUI-subsystem executable.

## Launch

1. Start Codex Quota Monitor from the Start menu.
2. Check whether the loading page explains that the local backend is starting
   and that the existing Codex sign-in is used.
3. Check whether the transition to the dashboard is clean and whether loading
   time feels acceptable.

## Main dashboard

The header shows the most recent sample time and a **Refresh** button. Refresh
requests an immediate collection, disables itself while it runs, then updates
the dashboard or shows the failure in the status line.

1. Can you understand current 5-hour usage and remaining quota immediately?
2. Can you understand weekly usage and remaining quota immediately?
3. Are the countdown reset labels clear?
4. Does weekly pace, its sustainable-pace ratio, and projected exhaustion need
   explanation? Which information feels unnecessary or missing?
5. Review full-reset availability, account plan, and credits where Codex
   supplies them.

## History

1. Review the seven-day weekly-usage graph, percentage grid, day labels, and
   four-hour tick marks.
2. Is the graph useful? Is the time scale and amount of history right?

## Window and background behavior

1. Close the dashboard window. It should hide to the notification tray while
   monitoring continues.
2. Use tray **Open** to restore the window.
3. Check the tray **Start at login** option. It is disabled by default.
4. Launch the app a second time. It should activate the existing instance,
   without another tray icon or collector.
5. Use tray **Quit**. Confirm the desktop shell and sidecar both exit.

## Diagnostics

Review these states in an isolated environment; do not alter real Codex
credentials.

- With Codex unavailable, the dashboard should remain stable and show the
  collector diagnostic rather than a crash.
- With authentication unavailable, the same controlled collector diagnostic
  should explain that a sample cannot be read.
- With a temporary collection failure, the status line should report the error
  while existing history remains available.
- With a sidecar startup or runtime failure, the loading page should say that
  Codex Quota Monitor needs attention instead of exposing a stack trace.

## Visual review

Record observations about colors, typography, density, spacing, window size,
information hierarchy, and anything that feels too technical. Check normal and
high-DPI Windows displays, including whether any text clips, any horizontal
scrollbar appears, or the history graph becomes hard to read.

## Owner decisions

### Must-have before public beta


### Nice-to-have later


### Remove or simplify


### Ideas for a mobile/iPhone companion
