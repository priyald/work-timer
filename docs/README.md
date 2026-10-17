# Work timer

A small floating animal that runs your work blocks and hands out breaks. Lives
above every other window, follows you across Spaces, and never steals focus.

    ./run.sh

Quit from the menu bar. There is no dock icon.

## The idea

A fixed pomodoro has one failure mode that matters here: it interrupts
hyperfocus, which is the expensive thing to lose, while doing nothing about the
days you forget to eat or forget to stop. So the timer does not hold one rhythm.
It runs in three **gears** and shifts between them based on what you actually do.

| Gear   | Work | Short break | Long break after |
|--------|------|-------------|------------------|
| choppy | 15m  | 5m          | 6 blocks         |
| steady | 25m  | 5m          | 4 blocks         |
| flow   | 50m  | 10m         | 2 blocks         |

Long breaks are 30 minutes in every gear.

## How it decides

When a break starts it is a nudge, not a wall. Two buttons:

- **+10 min** — you are in flow, push the break back. The break is still owed;
  it fires after the extra ten minutes. Capped at 3 pushes, and once they are
  spent the button stops offering a fourth instead of lying to you.
- **Break** (during work) — you tapped out early.

Each `+10` is a vote that your blocks are too short. Each early exit is a vote
that they are too long. Two votes in the same direction and the gear shifts on
its own: choppy → steady → flow, or back down. You never configure it. Turn it
off under *Pace → Adapt to how I'm working* if you want a fixed gear.

## Getting started is its own problem

**Just 5 min** sits next to Start. Five minutes is a much cheaper thing to agree
to than twenty five, and beginning is the hard part. After the five minutes it
quietly becomes a normal block and tells you so — you can stop whenever, it just
does not throw a break at you for a five minute stint.

## The two stops

Everything above runs itself. These do not move, and each fires on **whichever
comes first**, the hours or the clock, so a day that started at noon still ends
in the evening.

**Lunch — after 5h of work, or at 13:00.** Nothing counts down. It sits there
until you say you are back. The clock version only fires inside a 2.5 hour
window, because a lunch reminder at 18:40 is noise.

**Stop — after 8h of work, or at 18:30. Hard.** No "one more hour" button, no
way to click past it: a stop you can wave away in one tap is not a stop. The
only way out is deliberately restarting the day.

Neither fires until you have actually worked 20 minutes, so sitting down at
12:55 does not get you an instant lunch nag.

"Work time" means time in work blocks and meetings. Breaks and pauses do not
count, so a 9am–7pm day with proper breaks is about 8 hours of work.

## Meetings

Known windows in `config.json`. During one, the timer switches to a meeting
phase: it counts toward your hours, shows a count **up** so you can see how long
the call has run, and no break will ever interrupt it. An hour on a call counts
as one work block. **Done** ends it early without the window pulling you back in.

Currently set: Monday 11:15–12:15.

## The pet

A pixel creature, drawn rather than an emoji. It breathes, it blinks while
you work, and it changes expression with the phase: asleep before you start and
after you stop, alert while working, mouth moving during a meeting, pleased on a
break, eating at lunch.

There are no image files. Every frame is a grid of 16-character rows in
`timer/sprite.py`, so you can redraw the thing in a text editor. `animal` in
config picks fox, cat or bunny — the body is shared, the ears and fur change.

## Where it shows up

These are **two separate windows**, which matters. One panel doing both jobs
meant the widget had to move out of place every time you switched apps, which is
the opposite of a widget.

- **The desktop widget is fixed.** It sits behind every app window and above the
  desktop and its folders.

  It is at the *normal* window level, ordered to the back, rather than at the
  desktop level. That looks like the wrong choice and is not: macOS does not
  deliver mouse events to windows at the desktop level — Finder's desktop
  swallows them — which is why desktop widget apps ship a separate "interaction
  mode" that raises the level before you can click anything. Down there, Start
  and the restart button simply do nothing. An accessory app's window at the
  normal level, ordered back, ends up in the same place visually and takes
  clicks. It never resizes, never turns into anything else and never moves
  on its own. Switching to an app does not make it go anywhere — your windows
  simply cover it. Drag it where you want it; the position is remembered. It
  defaults to the bottom right, because the top right is where macOS puts its
  own widgets.

  Collapsed it shows one thing: the pet, the countdown and a progress bar.
  **Click it and the controls open** — restart, resume/pause, and break — the
  way clicking a widget opens its app. They close again when you click it a second
  time, after twelve seconds, or on anything that means you have moved on: a
  display being plugged in or out, switching to an app, or dragging the widget
  somewhere else. Dragging still moves it: a drag and a
  click start identically, so they are told apart by whether the mouse moved.

  Its position is stored as an offset **inside one named display**, not as
  absolute screen coordinates. Absolute coordinates only mean anything for one
  monitor arrangement: plug a second display in, or unplug one, and yesterday's
  numbers point somewhere else. Both panels also decline AppKit's offer to
  constrain them to a screen, which is what was shunting the widget around when
  displays changed.
- **The edge tab** appears only while an app is in front, which is exactly when
  the widget is covered. A sliver at the right edge, 15 points wide, floating
  above app windows but covering nothing you are reading. Click it for a compact
  card, which closes itself after ten seconds or on the **»** button.
- **Always** — the menu bar, which shows the phase and the countdown. This is
  the only strip on macOS that genuinely never covers an app's content, because
  the system reserves that space. Anything else floating at a screen edge would
  sit on top of your windows.

The **↻** in the controls restarts the day: one press and it is back at Start,
with nothing carried over — not the clock, not a half-finished pause, not a break
you were owed.

The **»** on the expanded edge card sends it back to the edge immediately,
rather than waiting out the ten seconds.

## Controls

The widget's controls have restart, the phase button, and break. The menu bar has the rest:
phase and time left, hours worked today, what the next break will be, gear
selection, hiding the pet while screen sharing, resetting the day, and quit.

## Settings

`config.json` next to `run.sh`. Restart the app after editing. Any key you
delete falls back to a sane default, and a broken file still starts the app.

`animal` accepts: fox, cat, bunny, frog, otter, penguin, duck, hedgehog.

## Layout

    main.py             entry point
    run.sh              launcher, finds a python3 with pyobjc
    config.json         your settings
    .today.json         today's totals, so a restart mid-afternoon does not
                        hand you a fresh 8 hour budget
    timer/
      schedule.py       the state machine. Every timing decision lives here and
                        nothing in it touches the screen
      timeline.py       wall-clock questions: meeting windows, "is it past 13:00"
      actions.py        what the two buttons mean in each phase
      widget.py         the fixed desktop widget
      edgetab.py        the sliver you reach it by from inside an app
      panels.py         shared window and control plumbing
      sprite.py         the pet, as pixel grids. No image files
      pixelview.py      draws a sprite grid, scaled to whatever space it has
      levels.py         window levels, read from CoreGraphics through ctypes
      presence.py       which app is frontmost, so the pet can get out of the way
      menubar.py        the status item and its menu
      pet.py            the animal, faces, and every phase-specific string
      notify.py         banners and chimes, shelled out to macOS
      fmt.py            time formatting
      config.py         load, merge with defaults, persist
      app.py            wiring
    tests/
      test_schedule.py  drives the schedule against a fake clock
      test_timeline.py  meeting windows and clock thresholds
      test_sprite.py    grid integrity: one short row draws a broken creature
      test_smoke.py     builds the real AppKit objects and renders every phase

Run them with:

    for t in tests/test_*.py; do python3 $t; done

The schedule keeps two clocks apart deliberately: durations use a monotonic
clock so a DST change cannot make a block jump, while stops and meetings use
wall-clock time, because "lunch by 13:00" is a question about the actual day.

## Notes

Notifications use `osascript` and sounds use `afplay`, so it needs no app bundle
and no code signing. If banners do not appear, allow Script Editor (or your
terminal) under System Settings → Notifications.

"Desktop" means Finder is frontmost. That is also true when a Finder window is
focused, so you may occasionally see the full widget over a file browser. That
is the best the public API gives us without accessibility permissions.

Do not move this folder onto the Desktop. `~/Desktop` is TCC-protected, and a
launchd job pointed at it fails with `Operation not permitted` — the same thing
that silently killed the weekly career automation. The Desktop entry is a symlink.
