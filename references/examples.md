# The example sources

`assets/examples/` holds 44 real Phosphor icons rebuilt as IconKit sources.
Each one, run through `iconkit.py build`, lands on the real icon's outlines to
within about 1% of its ink in thin, light and regular — most are exact — and
all but a handful match in fill and duotone too. `scripts/selftest.py` checks
this.

They are here to be **read and copied from**. When you need a file body, a
shield, a user, a check in a circle: open the example, take the element, change
what you need. A part lifted from these is guaranteed to be drawn the way
Phosphor draws it.

```bash
cat assets/examples/shield-check.svg                       # read a source
python3 scripts/iconkit.py sheet assets/examples/lock.svg lock -o /tmp/x.png   # source vs real, all weights
python3 scripts/iconkit.py show gauge duotone              # body centreline of ANY Phosphor icon
```

## By what they teach

| Pattern (see `weights.md`) | Examples |
|---|---|
| One closed body: `solid` + `tint` | `shield` `heart` `chat` `funnel` `lightning` `cloud` `house` |
| Body with knocked-out detail | `clock` `check-circle` `shield-check` `warning` `tag` `trash` `file-text` `magnifying-glass-plus` `key` |
| Body with strokes that stay strokes | `lock` `bell` `robot` `cpu` `magnifying-glass` `calendar-blank` |
| Open glyph on a plate | `plus` `list` `code` `terminal` |
| Open glyph, head closed instead | `arrow-right` |
| Several bodies, all solid | `tree-structure` `chart-bar` |
| Several bodies, one solid | `git-branch` `database` `stack` `envelope` `file` `folder` |
| A hole at the centreline | `eye` `gear` `file` (the fold) `calendar-blank` (the header) |
| A silhouette knockout | `toggle-left` |
| Solid painted back over a hole | `cpu` `globe` |
| Tint with a hole (`evenodd` plate) | `eye` `gear` `cpu` `robot` |
| Fill-only alternate geometry | `user` `user-plus` `chart-bar` `robot` `cloud-arrow-up` |
| Modifier inside a body | `magnifying-glass-plus` `shield-check` `check-circle` `cloud-arrow-up` `file-text` |
| Modifier beside a body | `user-plus` `sparkle` |
| The slash (`data-gap`) | `bell-slash` |

## By what they contain

| Need | Take it from | The element |
|---|---|---|
| Person: head and shoulders | `user` | circle `128,96 r=64`; arc `M32,216c19.37-33.47,54.55-56,96-56s76.63,22.53,96,56` |
| Person, making room for a modifier | `user-plus` | circle `108,100 r=60`; arc spanning 24..192 |
| Document with folded corner | `file` | body path, fold polyline `152,32 152,88 208,88` |
| Text lines on a document | `file-text` | lines `96→160` at y=136 and y=168 |
| Folder with tab | `folder` | body and tab paths |
| Shield | `shield` | one path, 40..216 × 48..232 |
| Bell with clapper | `bell` | body path; arc `M96,192a32,32,0,0,0,64,0` |
| Cloud | `cloud` | one open path of two arcs |
| Speech bubble with tail | `chat` | one path |
| Padlock | `lock` | rect `40,88 176×128 rx=8`; shackle `M88,88V56a40,40,0,0,1,80,0V88`; dot `128,152` |
| Key | `key` | one path; dot `180,76` |
| Gear, eight teeth | `gear` | one path; circle `r=40` |
| Cylinder / database | `database` | ellipse `128,80 rx=88 ry=48`; two side paths |
| Eye | `eye` | lens path; circle `r=40` |
| Lens and handle | `magnifying-glass` | circle `112,112 r=80`; line `168.57,168.57→224,224` |
| Clock face | `clock` | circle `r=96`; hands polyline |
| Calendar | `calendar-blank` | square; pegs at x=80, 176; rule at y=88 |
| Envelope | `envelope` | body path; flap polyline |
| House | `house` | one closed path including the door notch |
| Tag | `tag` | one path; dot `84,84` |
| Trash can | `trash` | lid line; body path; handle path; two lines |
| Funnel | `funnel` | one path |
| Stacked layers | `stack` | diamond polygon; two chevrons |
| Bar chart | `chart-bar` | base line; three step polylines |
| Nodes joined by lines | `git-branch` | circles `r=24`; connector path with `r=16` bends |
| Boxes joined by lines | `tree-structure` | rects `rx=8`; elbow path |
| Chip | `cpu` | square `48,48 160×160 rx=8`; inner square; eight pins |
| Robot head | `robot` | rect `32,56 192×160 rx=24`; mouth pill; dots; antenna |
| Toggle | `toggle-left` | pill; knob circle `80,128 r=32` |
| Globe | `globe` | circle; two latitude lines; one meridian path |
| Four-point sparkle + small pluses | `sparkle` | star path; pluses 48 and 32 wide |
| Lightning bolt | `lightning` | polygon `96,240 112,160 48,136 160,16 144,96 208,120` |
| Heart | `heart` | one path |
| Warning triangle | `warning` | rounded triangle path; `!` |
| Code brackets, prompt | `code` `terminal` | polylines |

## Where they differ from Phosphor on purpose

Phosphor hand-tunes a few fills beyond what a simple rule produces. These
examples keep the simple version, so that what you copy is the pattern and not
the special case: `house` (Phosphor widens the door in fill), `cloud` and
`cloud-arrow-up` (Phosphor adds a curl), `globe` (Phosphor fills alternate
sectors), `key` (Phosphor enlarges the knocked-out dot to r=16). `bell-slash`
cuts the bell flat beside the slash where Phosphor re-caps each cut end by
hand; at icon sizes the two are indistinguishable.

No example adjusts bold. For about a third of these icons Phosphor's bold is
not a plain 24-unit stroke — details are moved or shrunk by hand, for the
reasons in `weights.md` §8 — which is a fair picture of how often your own
bold will want a second look.
