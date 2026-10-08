# Adding the icon to a Figma library

Optional, and never automatic. A design file is shared with other people and
has conventions of its own; the job here is to add the new icon the way that
file already does things, somewhere it cannot disturb existing work.

**Contents** — 1 Ask first · 2 Connect · 3 Read the file's conventions ·
4 Say the plan · 5 Build the components · 6 Check and report · 7 If there is no
Figma connection

---

## 1. Ask first

Only after the SVGs are built and the user has seen the preview, ask — in one
message — both things you need:

> Want me to add `gauge-limit` to your Figma icon library as components? If so,
> which file — paste its link, or tell me it's the one open in Figma now.

Do nothing in Figma until the user has said yes *and* named the file. A yes for
one icon is not a yes for the next one in a later request; ask again.

## 2. Connect

Use whichever Figma tool this session has that can run Plugin API JavaScript
in the file. Two are common; check what is available rather than assuming.

- **Figma's own MCP server** (`use_figma` and friends). It ships a usage skill
  (`figma-use`) that must be loaded before the first call; do that, and follow
  its calling conventions. It takes the file's URL.
- **A console/bridge server** (`figma_execute`, `figma_take_screenshot`, …). It
  acts on the file open in Figma desktop with its bridge plugin running. List
  the connected files and confirm the active one is the file the user named
  before writing anything.

The scripts below are Plugin API code and work in either; adapt the wrapper
(how the code returns a value) to the tool.

If the file the user named is not the one you are connected to, stop and say
so. Writing icons into the wrong file is the one mistake here that is hard to
notice and tedious to undo.

## 3. Read the file's conventions

Before creating anything, find out how icons are built in this file. Run this
read-only survey (it looks for a few icons every Phosphor library has):

```js
await figma.loadAllPagesAsync();
const probe = ["bell", "house", "gear", "user", "lock", "heart", "star", "check", "plus"];
const tokens = s => s.toLowerCase().split(/[^a-z0-9]+/).filter(Boolean);
const where = n => { const p = []; for (let a = n.parent; a && a.type !== "DOCUMENT"; a = a.parent) p.unshift(a.type + ":" + a.name); return p.join(" > "); };
const paint = v => ({
  fills: "fills" in v && v.fills !== figma.mixed ? v.fills.map(f => ({ type: f.type, visible: f.visible, opacity: f.opacity, color: f.color, variable: f.boundVariables && f.boundVariables.color ? f.boundVariables.color.id : null })) : "mixed",
  fillStyleId: "fillStyleId" in v && v.fillStyleId !== figma.mixed ? v.fillStyleId : null,
  strokes: "strokes" in v ? v.strokes.length : 0, strokeWeight: "strokeWeight" in v && v.strokeWeight !== figma.mixed ? v.strokeWeight : null,
});
const describe = c => ({
  name: c.name, w: c.width, h: c.height, clips: c.clipsContent, background: c.fills === figma.mixed ? "mixed" : c.fills.length,
  layers: c.findAll(() => true).slice(0, 6).map(l => ({ type: l.type, name: l.name, opacity: l.opacity, constraints: "constraints" in l ? l.constraints : null, x: l.x, y: l.y, w: l.width, h: l.height, ...paint(l) })),
});
const found = [];
let total = 0;
for (const page of figma.root.children) {
  for (const n of page.findAllWithCriteria({ types: ["COMPONENT_SET", "COMPONENT"] })) {
    if (n.type === "COMPONENT" && n.parent && n.parent.type === "COMPONENT_SET") continue;
    total++;
    if (!tokens(n.name).some(t => probe.includes(t)) || found.length >= 14) continue;
    found.push({
      page: page.name, where: where(n), type: n.type, name: n.name, x: n.x, y: n.y, w: n.width, h: n.height,
      properties: n.type === "COMPONENT_SET" ? Object.fromEntries(Object.entries(n.componentPropertyDefinitions).map(([k, d]) => [k, d.variantOptions || d.type])) : null,
      variants: n.type === "COMPONENT_SET" ? n.children.slice(0, 8).map(describe) : [describe(n)],
    });
  }
}
return { file: figma.root.name, pages: figma.root.children.map(p => p.name), componentCount: total, found };
```

From the result, write down — for yourself — the answers to six questions:

1. **One component per icon, or one per weight?** A `COMPONENT_SET` with a
   variant property (often `Weight`, `Style` or `Type`) means one set per icon.
   Separate components named like `bell-bold`, `bell/bold` or `Bold/bell`,
   perhaps on a page per weight, means one per weight.
2. **Which weights exist, and what are they called exactly?** `Regular` or
   `regular`? Is duotone there at all? Match spelling and case, and the order.
3. **How are icons named?** `bell`, `Bell`, `Icon/Bell`, `ph-bell`?
4. **What size is the frame?** 16, 20, 24, 32, 256. Does the vector fill it, or
   sit inside padding?
5. **What is inside?** One flattened vector with a fill (outlined — what
   Phosphor ships, and what IconKit builds), or live strokes? What is the
   layer called? What are its constraints?
6. **How is it coloured?** A local fill, a paint style (`fillStyleId`), or a
   variable. New icons must use the same one or they will not follow the
   library's theming.

If the survey finds nothing — the file has no Phosphor-named components —
do not guess. Tell the user what you looked for, and ask how their icons are
organised or which component to copy the structure of. If they have no
convention yet, propose this default and wait for a yes: one component set per
icon, named in kebab-case, with a `Weight` property (`Thin`, `Light`,
`Regular`, `Bold`, `Fill`, `Duotone`), 32 × 32 frames, one flattened vector
named `Vector`, constraints `SCALE`, fill black.

If the file's icons are **live strokes**, say so before continuing: IconKit's
output is outlined, like Phosphor's own files. Outlined icons work everywhere,
but they will not respond to a stroke-weight override. The user decides.

## 4. Say the plan

One short message before writing, so the user can catch a wrong assumption
while it is still free to fix:

> I'll add a component set `gauge-limit` (6 weights, 32 px, same structure and
> `Icon/Primary` fill as `bell`) to a new "IconKit" section on the *Icons*
> page, to the right of the existing grid. Nothing existing is touched.

Then proceed; the user already said yes in step 1. Stop and ask only if the
survey showed two conflicting conventions, or a component with this name
already exists (replace it, or add alongside? — their call).

## 5. Build the components

Read the six built SVG files and paste each one's full text into `SVG` below.
Set the constants from what the survey found. This is the one-set-per-icon
version; the notes after it cover the other structure.

```js
const ICON = "gauge-limit";
const PAGE = "Icons";                       // page name from the survey
const SIZE = 32;                            // frame size from the survey
const LAYER = "Vector";                     // vector layer name from the survey
const PROP = "Weight";                      // variant property from the survey
const LABEL = { thin: "Thin", light: "Light", regular: "Regular", bold: "Bold", fill: "Fill", duotone: "Duotone" };
const COPY_PAINT_FROM = "1:23";             // id of an existing icon's vector layer, or null for black
const SVG = { thin: `…`, light: `…`, regular: `…`, bold: `…`, fill: `…`, duotone: `…` };

await figma.loadAllPagesAsync();
const page = figma.root.children.find(p => p.name === PAGE);
await figma.setCurrentPageAsync(page);
if (page.findOne(n => (n.type === "COMPONENT_SET" || n.type === "COMPONENT") && n.name === ICON)) {
  return { stopped: `a component named ${ICON} already exists on ${PAGE}` };
}

// A section of our own, clear of everything already on the page.
let section = page.findOne(n => n.type === "SECTION" && n.name === "IconKit");
if (!section) {
  section = figma.createSection();
  section.name = "IconKit";
  let right = -Infinity, top = Infinity;
  for (const n of page.children) if (n !== section) { right = Math.max(right, n.x + n.width); top = Math.min(top, n.y); }
  section.x = isFinite(right) ? right + 240 : 0;
  section.y = isFinite(top) ? top : 0;
  section.resizeWithoutConstraints(6 * (SIZE + 24) + 96, SIZE + 144);
}
let below = 48;
for (const n of section.children) below = Math.max(below, n.y + n.height + 48);

const ref = COPY_PAINT_FROM ? await figma.getNodeByIdAsync(COPY_PAINT_FROM) : null;
const made = [];
for (const w of Object.keys(LABEL)) {
  const imported = figma.createNodeFromSvg(SVG[w]);       // a 256×256 frame holding one vector per path
  const comp = figma.createComponent();
  comp.resizeWithoutConstraints(256, 256);
  comp.fills = [];
  comp.clipsContent = false;
  const vectors = imported.findAll(n => n.type === "VECTOR");
  for (const v of vectors) {
    const tint = v.opacity < 1;                            // duotone's 20% layer comes first
    comp.appendChild(v);
    v.name = tint ? LAYER + " (tint)" : LAYER;
    v.constraints = { horizontal: "SCALE", vertical: "SCALE" };
    if (ref) {
      if (ref.fillStyleId && ref.fillStyleId !== figma.mixed) await v.setFillStyleIdAsync(ref.fillStyleId);
      else if (ref.fills !== figma.mixed) v.fills = JSON.parse(JSON.stringify(ref.fills));
    }
  }
  imported.remove();
  comp.rescale(SIZE / 256);
  comp.name = `${PROP}=${LABEL[w]}`;
  section.appendChild(comp);
  made.push(comp);
}
const set = figma.combineAsVariants(made, section);
set.name = ICON;
set.x = 48; set.y = below;
set.layoutMode = "HORIZONTAL"; set.itemSpacing = 24;
set.paddingLeft = set.paddingRight = set.paddingTop = set.paddingBottom = 24;
set.primaryAxisSizingMode = "AUTO"; set.counterAxisSizingMode = "AUTO";
section.resizeWithoutConstraints(Math.max(section.width, set.x + set.width + 48), Math.max(section.height, set.y + set.height + 48));
return { setId: set.id, section: section.id, variants: made.map(c => ({ id: c.id, name: c.name })) };
```

**Adapting it**

- *One component per weight*: skip `combineAsVariants`. Name each component
  the way the survey showed (`gauge-limit-bold`, `Bold/gauge-limit`, …) and put
  each on the page or in the frame where that weight's icons live — still in
  an "IconKit" section there, not threaded into the existing grid.
- *Padding inside the frame*: if existing vectors sit inside a margin (say a
  24 px frame with a 20 px drawing), scale to the drawing size and centre it,
  rather than filling the frame.
- *Colour by variable*: copying `fills` carries the variable binding. Confirm
  it afterwards by reading the new vector's `fills[0].boundVariables`.
- *Duotone*: keep both vectors. If the library's duotone components name their
  two layers, use those names. The tint layer keeps `opacity: 0.2` and the same
  colour as the main layer.
- *Descriptions*: if existing components carry a description or search
  keywords, add the same for the new one (the feature it is for, and a few
  synonyms), so designers can find it.

Never edit, move or reorder a component that was already there. Never publish
the library; that is the user's decision and their click.

## 6. Check and report

Take a screenshot of the new set next to an existing one at the same zoom and
look at it, the same way as `preview.png`: same size in its frame, same visual
weight, colour following the library. If the import shows a problem that the
preview did not (a filled-in counter means a winding issue; a shifted layer
means constraints were set before the move), remove what you made, fix it and
redo it rather than leaving a half-right component in a shared file.

Then tell the user where it is, in words and with a link to the node:
`https://www.figma.com/design/<fileKey>/?node-id=<id with : replaced by ->`.
Say what you matched (structure, size, colour) and anything you could not
match. Remind them the library needs publishing before other files see it.

## 7. If there is no Figma connection

Say so plainly and give them the manual route, which takes a minute: drag the
six SVG files from the icon's folder onto the Figma canvas; each lands as a
frame with a single flattened vector, already outlined. Offer to redo it
properly once a Figma tool is connected.
