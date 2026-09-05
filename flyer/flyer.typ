// Alum Rock Park habitat restoration flyer — starter plant guide.
// Two letter-size pages: native plants (front), invasive targets (back).

#let moss = rgb("2f4a3a")
#let moss-dark = rgb("1f3327")
#let bark = rgb("6b4a2f")
#let clay = rgb("b5511e")
#let gold = rgb("c79a2e")
#let gold-text = rgb("3a2e05")
#let paper = rgb("f6f3e9")
#let ink = rgb("25281f")
#let line-color = rgb("c9c1a8")
#let card-native = rgb("eef1e6")
#let card-invasive = rgb("f4e9de")
#let sci-color = rgb("4a4638")
#let desc-color = rgb("3a3728")
#let note-color = rgb("5a5645")
#let attribution-color = rgb("857f68")

#let margin-x = 0.5in
#let margin-y = 0.4in
#let content-w = 8.5in - 2 * margin-x
#let gutter = 0.14in
#let col-w = (content-w - 2 * gutter) / 3

#set page(width: 8.5in, height: 11in, margin: (x: margin-x, y: margin-y), fill: paper)
#set text(font: ("Arial", "Helvetica"), size: 9pt, fill: ink)

// ---------- shared components ----------

#let masthead(title, date) = block(
  width: 100%,
  stroke: (bottom: 3pt + moss),
  inset: (bottom: 9pt),
  below: 12pt,
)[
  #grid(
    columns: (1fr, auto),
    align: (left + bottom, right + bottom),
  )[
    #text(font: "Georgia", weight: "bold", size: 17pt, fill: moss-dark)[#title]
  ][
    #text(size: 9pt, fill: bark)[#date]
  ]
]

#let why-box(body) = block(
  width: 100%,
  fill: moss-dark,
  radius: 4pt,
  inset: (x: 16pt, y: 10pt),
  below: 14pt,
  breakable: false,
)[
  #text(fill: paper, size: 9.5pt)[#body]
]

#let section-label(title, accent) = block(below: 8pt)[
  #box(baseline: 30%, fill: accent, width: 5pt, height: 14pt)
  #h(8pt)
  #text(font: "Georgia", weight: "bold", size: 14pt)[#title]
]

// A plant photo with its lifecycle badge (A/P) and, for extra-concern
// invasives, a warning flag — placed via `place()` so stacking order is
// explicit instead of depending on DOM/paint order like the HTML version did.
#let plant-photo(photo, height, lifecycle, concern: false) = box(
  width: 100%,
  height: height,
  radius: 2pt,
  clip: true,
)[
  #image(photo, width: 100%, height: 100%, fit: "cover")
  #let badge-fill = if lifecycle == "A" { gold } else { bark }
  #let badge-text = if lifecycle == "A" { gold-text } else { white }
  #place(top + right, dx: -6pt, dy: 6pt)[
    #box(
      fill: badge-fill,
      stroke: 1.5pt + rgb("ffffffcc"),
      radius: 5pt,
      width: 20pt,
      height: 20pt,
    )[
      #align(center + horizon)[
        #text(fill: badge-text, weight: "bold", size: 12pt)[#lifecycle]
      ]
    ]
  ]
  #if concern [
    #place(top + left, dx: 5pt, dy: 4pt)[#text(size: 15pt)[⚠️]]
  ]
]

#let card-inset = 7pt
#let desc-size = 8.5pt

// Both the name/scientific-name line and the description vary in length —
// a long scientific name wraps to a second line, and descriptions run
// short or long — so left to their natural height, cards in the same row
// would end at different heights. `names-height`/`desc-height` (each
// measured once, below, as the tallest across all 12 plants) fix both
// slots to the same size regardless of a given card's own text length, so
// every card comes out exactly the same total height.
#let plant-card(
  name,
  sci,
  lifecycle,
  photo,
  photo-height,
  desc,
  names-height,
  desc-height,
  native: true,
  concern: false,
) = {
  let accent = if native { moss } else { clay }
  let bg = if native { card-native } else { card-invasive }
  block(
    width: col-w,
    fill: bg,
    stroke: (left: 4pt + accent, rest: 1pt + line-color),
    radius: 3pt,
    inset: card-inset,
    breakable: false,
  )[
    #plant-photo(photo, photo-height, lifecycle, concern: concern)
    #v(6pt)
    #box(width: 100%, height: names-height)[
      #text(weight: "bold", size: 11pt)[#name]
      #h(4pt)
      #text(style: "italic", size: 9pt, fill: sci-color)[#sci]
    ]
    #v(3pt)
    #box(width: 100%, height: desc-height)[
      #text(size: desc-size, fill: desc-color)[#desc]
    ]
  ]
}

#let plant-grid(cards) = grid(
  columns: (col-w, col-w, col-w),
  column-gutter: gutter,
  row-gutter: gutter,
  ..cards
)

#let legend-swatch(label, fill, text-color) = box(
  fill: fill,
  radius: 4pt,
  width: 15pt,
  height: 15pt,
)[
  #align(center + horizon)[#text(fill: text-color, weight: "bold", size: 9pt)[#label]]
]

#let legend-item(swatch, body) = grid(
  columns: (15pt, auto),
  column-gutter: 8pt,
  align: (center + horizon, horizon),
)[#swatch][#text(size: 9pt)[#body]]

#let key-box(items) = block(
  width: 100%,
  stroke: 1pt + line-color,
  radius: 4pt,
  inset: (x: 12pt, y: 5pt),
  below: 5pt,
  breakable: false,
)[
  #grid(columns: (1fr, 1fr), column-gutter: 20pt, row-gutter: 3pt, ..items)
]

#let footer-note(body) = align(center)[
  #block(above: 10pt, below: 12pt)[
    #text(font: "Georgia", weight: "bold", size: 24pt, fill: gold)[?]
    #h(7pt)
    #text(size: 12pt, weight: "bold", fill: note-color)[#body]
  ]
]

#let cta(heading, body, contact) = block(
  width: 100%,
  fill: moss,
  radius: 4pt,
  inset: (x: 14pt, y: 5pt),
  below: 4pt,
  breakable: false,
)[
  #text(font: "Georgia", weight: "bold", size: 12pt, fill: paper)[#heading]
  #v(1pt)
  #text(size: 9pt, fill: paper)[#body]
  #v(2pt)
  #text(size: 9pt, weight: "bold", fill: gold)[#contact]
]

#let attributions(body) = align(center)[
  #text(size: 8pt, fill: attribution-color)[#body]
]

// ---------- shared page content ----------
// Page 1's chrome (masthead + why-box) and page 2's chrome (key + footer +
// CTA + attributions) are unrelated in content but need to occupy the same
// vertical space, so that both grids get equal room and can share one photo
// ratio. Measure both, then pad the shorter one to match — Typst's
// `measure`/`context` make this exact instead of hand-tuned guesswork.

#let masthead-content = masthead("Alum Rock Park Habitat Restoration: Key Plants", "Sep 2026")
#let why-content = why-box[
  The Alum Rock Trail Crew is a community-based volunteer group that works on
  trail maintenance and habitat restoration in the Park. We remove invasive
  plants so native ecosystems can thrive, as well as reducing fuel and fire
  danger. We are drawn together by a special connection to the Park and a
  shared interest in conservation and improving the visitor experience at San
  José's oldest park.

  #text(fill: gold, weight: "bold")[Get involved:] Join us Monday and
  Wednesday mornings, or the second Saturday of each month — arp\@example.com.
]
#let top-matter = box(width: content-w)[#masthead-content #why-content]

#let bottom-matter = box(width: content-w)[
  #key-box((
    legend-item(legend-swatch("A", gold, gold-text))[*Annual* — new plant each year, pull \& compost],
    legend-item(legend-swatch("P", bark, white))[*Perennial* — regrows from roots, dig up fully],
    legend-item(box(width: 15pt, height: 15pt)[#align(center+horizon)[#text(size: 12pt)[⚠️]]])[*Bag \& remove* — too vigorous for compost piles to kill],
    [],
  ))
  #footer-note[Not sure what you're seeing? Ask someone in a volunteer t-shirt!]
  #attributions[
    Photos via iNaturalist: Coyote Brush © LSchare (she/her); California
    Sagebrush © Ryan Masters; Milk Thistle © Konstantinos Kalaentzis; Mustard
    © Amy; Yellow Star Thistle © Ken-ichi Ueda; all other photos © Kimberly
    Nicholls.
  ]
]

// shared by both grids so native/invasive photo areas match exactly
#let photo-ratio = 0.95

#context {
  let top-h = measure(top-matter).height
  let bottom-h = measure(bottom-matter).height
  let pad = calc.abs(top-h - bottom-h)

  // ---------- page 1: native plants ----------

  masthead-content
  if top-h < bottom-h { v(pad / 2) }
  why-content
  if top-h < bottom-h { v(pad / 2) }

  section-label("Native plants support the park's ecosystem", moss)

  let ph = col-w * photo-ratio

  // All 12 descriptions, measured once so every card's description slot
  // can be fixed to the tallest one — see `plant-card`'s desc-height.
  let descs = (
    "Evergreen coast live oaks and deciduous valley and blue oaks. These iconic trees anchor the whole ecosystem, feeding and sheltering more wildlife than almost any other native plant.",
    "A small-leaved evergreen shrub with fuzzy white seed heads in fall. It's a keystone species, hosting far more insects, birds, and other wildlife than most other native plants.",
    "A soft shrub with delicate, silvery grey-green foliage. Brushing the leaves releases a sage-like scent, making it easy to identify by smell alone.",
    "A low, sticky herb whose leaves smell strongly of vinegar when crushed. It's tough enough to keep blooming through the driest part of late summer, when little else is flowering.",
    "A sticky-stemmed herb with cheerful yellow flowers. It blooms late into the dry season, offering a rare source of nectar when most other plants have gone dormant.",
    [*Do not touch.* Its oils cause an itchy rash in most people, but birds and deer rely on its berries and leaves. Look for its bright red color in fall.],
    "A spiny plant with white-marbled leaves and purple flower heads. It spreads quickly by seed and crowds out natives, so pull it before it flowers and add it to compost.",
    "A spiny plant with tall stalks and clustered pink-purple flowers. It forms dense stands that block trails and crowd out natives, so dig it up before it flowers.",
    "A plant with fuzzy, wrinkled grey-green leaves and a minty smell. It spreads aggressively along disturbed ground and regrows from its roots, so dig up the whole plant.",
    "A fast-spreading plant with small yellow flowers, abundant throughout the park. It regrows from its roots and can quickly dominate open ground, so dig up the whole plant.",
    "A plant with sharp yellow spines that favors disturbed trail edges. It's toxic to horses and spreads aggressively, so bag it for removal instead of composting.",
    "A sticky, strong-smelling plant that can cause allergic skin reactions on contact. It spreads readily along trails, so bag it for removal instead of composting.",
  )
  // Same idea for the name/scientific-name line: a long scientific name
  // wraps to two lines, so measure all 12 pairs and fix every card's name
  // slot to the tallest one too.
  let names = (
    ("Oaks", "Quercus spp."),
    ("Coyote Brush", "Baccharis pilularis"),
    ("California Sagebrush", "Artemisia californica"),
    ("Vinegar Weed", "Trichostema lanceolatum"),
    ("Tarweed", "Holocarpha virgata"),
    ("Poison Oak", "Toxicodendron diversilobum"),
    ("Milk Thistle", "Silybum marianum"),
    ("Italian Thistle", "Carduus pycnocephalus"),
    ("White Horehound", "Marrubium vulgare"),
    ("Mustard", "Hirschfeldia incana"),
    ("Yellow Star Thistle", "Centaurea solstitialis"),
    ("Stinkwort", "Dittrichia graveolens"),
  )
  let desc-w = col-w - 2 * card-inset
  let dh = descs.map(d => measure(box(width: desc-w)[#text(size: desc-size)[#d]]).height)
  let desc-height = calc.max(..dh)
  let nh = names.map(n => measure(box(width: desc-w)[
    #text(weight: "bold", size: 11pt)[#n.at(0)]
    #h(4pt)
    #text(style: "italic", size: 9pt)[#n.at(1)]
  ]).height)
  let names-height = calc.max(..nh)

  plant-grid((
    plant-card(
      "Oaks", "Quercus spp.", "P", "print-photos/oak.jpg", ph, descs.at(0), names-height, desc-height,
    ),
    plant-card(
      "Coyote Brush", "Baccharis pilularis", "P", "print-photos/coyote_brush.jpg", ph, descs.at(1), names-height, desc-height,
    ),
    plant-card(
      "California Sagebrush", "Artemisia californica", "P", "print-photos/ca_sagebrush.jpg", ph, descs.at(2), names-height, desc-height,
    ),
    plant-card(
      "Vinegar Weed", "Trichostema lanceolatum", "A", "print-photos/vinegar_weed.jpg", ph, descs.at(3), names-height, desc-height,
    ),
    plant-card(
      "Tarweed", "Holocarpha virgata", "A", "print-photos/tarweed.jpg", ph, descs.at(4), names-height, desc-height,
    ),
    plant-card(
      "Poison Oak", "Toxicodendron diversilobum", "P", "print-photos/poison_oak.jpg", ph, descs.at(5), names-height, desc-height,
    ),
  ))

  pagebreak()

  // ---------- page 2: invasive plants ----------

  section-label("Invasive plants targeted for removal", clay)

  plant-grid((
    plant-card(
      "Milk Thistle", "Silybum marianum", "A", "print-photos/milk_thistle.jpg", ph, descs.at(6), names-height, desc-height,
      native: false,
    ),
    plant-card(
      "Italian Thistle", "Carduus pycnocephalus", "A", "print-photos/italian_thistle.jpg", ph, descs.at(7), names-height, desc-height,
      native: false,
    ),
    plant-card(
      "White Horehound", "Marrubium vulgare", "P", "print-photos/horehound.jpg", ph, descs.at(8), names-height, desc-height,
      native: false,
    ),
    plant-card(
      "Mustard", "Hirschfeldia incana", "P", "print-photos/mustard.jpg", ph, descs.at(9), names-height, desc-height,
      native: false,
    ),
    plant-card(
      "Yellow Star Thistle", "Centaurea solstitialis", "P", "print-photos/yellow_star.jpg", ph, descs.at(10), names-height, desc-height,
      native: false,
      concern: true,
    ),
    plant-card(
      "Stinkwort", "Dittrichia graveolens", "P", "print-photos/stinkwort.jpg", ph, descs.at(11), names-height, desc-height,
      native: false,
      concern: true,
    ),
  ))

  if bottom-h < top-h { v(pad) }
  bottom-matter
}
