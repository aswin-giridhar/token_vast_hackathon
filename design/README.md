# ClipScout — design pass

Proposal only. **No file outside `design/` is touched**, so this cannot conflict with Track
A's work on `index.html`. Take it, take part of it, or drop it.

| File | What it is |
| --- | --- |
| `demo-theme.css` | The whole change. Paste at the end of the existing `<style>` in `index.html` |
| `preview.html` | Standalone mockup with fake data, so you can see it before applying |
| `variant-a-full.png` | Screenshot of that preview at 1600×900 |

```bash
python -m http.server 8777 --directory design   # then open /preview.html
```

Every rule only overrides an existing one. Deleting the block restores the current design
exactly. No markup, no JavaScript and no new network request — except the one optional hook
in section 3, which is documented at the top of `demo-theme.css`.

## What this is optimising for

Not beauty. **A two-minute demo, on a projector, judged by people standing three metres
away who have already seen a dozen search boxes today.**

That reframes the problems. The current design is considered and coherent — good palette,
proper `<dialog>` use, real responsive breakpoints. It is built for someone sitting at a
desk. The judging happens under different conditions.

## The seven changes

### 1. Type scale

Sizes of 10px and 11px carry the camera ID, the timecode, the relevance score and the
coverage counter — the provenance that is the product's whole argument. None of it is
readable when projected. Everything below 13px was raised. Nothing structural moved.

### 2. Reclaim the fold

The hero was a 52px headline plus a subtitle plus a metric, after a 76px header and 35px of
padding. The first row of results began roughly 400px down a 900px viewport.

Now the headline is 25px, the subtitle is hidden, and **the search box, the summary and the
first row of cards all sit above the fold.** The first thing a judge sees is the product
working, not the brand.

### 3. Show the summary you already fetch

`main.py` line 133 pulls `llm_synthesis.response` into `search()`'s return value as
`summary`. `index.html` never reads it.

The challenge is called *video search **and summary***. You have the summary and throw it
away. This is the one change needing a markup hook — two lines, both at the top of
`demo-theme.css`. **Highest value per minute in this whole folder.**

### 4. Relevance as a bar, not a decimal

`Similarity 0.57` reads as a confidence probability. It is a ranking score, and your own
README says so. The card now shows rank position and a bar; the status line keeps the
caveat. Same information, one fewer way to be misread.

### 5. The scene gap becomes a first-class action

This was a `.small` secondary button, hidden until a search returned nothing, placed below
the grid.

It is **the strongest claim the product makes** — a system that refuses to substitute
footage rather than returning the nearest wrong clip. It is now a standing full-width panel
in warning orange, visible on every search, reading *"None of these fit the shot? Record a
scene gap. The request stays open and nothing is substituted into your cut."*

If a judge remembers one thing, this should be it. Lead the demo with it rather than
reaching step 4.

### 6. Coverage as a progress bar

`1 / 3 covered` in 12px grey was the only indicator of the thing the entire desk works
toward. Now a bar, with the count at 13px semibold.

### 7. Card legibility

Camera and timecode promoted out of 11px grey into tabular numerals at readable weight;
hover state on cards; two columns below 1450px so thumbnails stay large on a laptop.

## Two bugs found while building this

Worth knowing, because both are in the current stylesheet's blast radius:

- **`.hero p` also matches the metric's `<p>`.** `.metric` is nested inside `.hero`, so a
  rule hiding the hero subtitle silently hides `INDEXED SEGMENTS` too. I hit this in my own
  override and had to restore it explicitly. If you ever add a `.hero p` rule, check the
  metric.
- **Hiding the `<br>` in the headline joins the sentences** into
  `Find the moment.Build the story.` with no space. The theme keeps the `<br>` and shrinks
  the type instead.

## What I did not do

- No colour changes. The palette is good and relighting it is risk without reward.
- No layout restructure. A two-pane editorial workstation would suit the task better, but
  that is an hour of work in Codex's file on submission day.
- No change to the review dialog or the cut tab beyond type scale, because I could not test
  them against real data.

## Caveat

Built against a static mockup with fake content, **not the deployed app**. Card heights with
real descriptions, the video player and the review dialog are unverified. Apply it, open the
deployed URL, and look at it before trusting any of this.

## Stitch exploration

A parallel generated concept is at
[stitch.google.com/projects/8395511098178602186](https://stitch.google.com/projects/8395511098178602186)
— two screens, *Archive Search Desk* and *Your First Cut Desk*. It is a direction for a
future redesign, not something to paste in today; `demo-theme.css` is the shippable version.
