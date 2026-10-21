'use strict';
/* English versions of the info windows (bilgi.js holds the Turkish ones).
   Written as English metallurgy text, not a word-for-word translation.
   Numerical examples come from this application's own calculation. */

const BILGI_EN = {
  /* ------------------------------------------------------------------ */
  diyagram: {
    baslik: 'How to read the diagram',
    html: `
<p>This diagram is not a picture: every boundary is drawn from a computer calculation of thermodynamic equilibrium (the CALPHAD method).
The horizontal axis is <b>carbon content</b> (wt%), the vertical axis is <b>temperature</b>. Each point answers the question
"which phases will this steel consist of if it is held long enough at this temperature?"</p>
<h4>Colors and patterns</h4>
<ul>
  <li><b>Solid color</b>: single-phase field (austenite only, ferrite only…).</li>
  <li><b>Hatched</b>: two or more phases coexist; the stripe colors are those phases.</li>
  <li><b>Black dots</b>: invariant points (eutectoid, eutectic, peritectic).</li>
  <li><b>Orange dashed lines</b>: your chosen carbon (vertical) and temperature (horizontal); where they cross is the selected point.</li>
  <li>In a two-phase field, the <b>thick orange line</b> through the selected point is the tie-line: its ends give the carbon content of each phase.</li>
</ul>
<h4>Controls</h4>
<table>
  <tr><td>Click / drag</td><td>Pick a point, drag to explore</td></tr>
  <tr><td><kbd>Shift</kbd> + click</td><td>Pin a point for comparison; hover over it to see its card</td></tr>
  <tr><td>Click / right-click a pin</td><td>Move the orange point there / remove the pin</td></tr>
  <tr><td>Mouse wheel</td><td>Zoom in around the cursor</td></tr>
  <tr><td><kbd>←</kbd> <kbd>→</kbd> <kbd>↑</kbd> <kbd>↓</kbd></td><td>Move the point with the keyboard when the diagram has focus (<kbd>Shift</kbd> for 10× steps)</td></tr>
  <tr><td>View buttons</td><td>Jump to frequently used regions (steel range, eutectoid corner…)</td></tr>
</table>
<h4>A metastable diagram</h4>
<p>What you see is the Fe–Fe₃C (iron–cementite) diagram. Strictly, graphite is the stable carbon phase, but it forms so slowly in steels
that cementite forms in practice, so graphite is excluded from the calculation. The stable (Fe–graphite) diagram is the one used to
explain gray and ductile cast irons.</p>
<div class="ozet">The diagram shows <b>equilibrium</b>. Structures formed on fast cooling, such as martensite and bainite, do not appear on it;
see the "Cooling & hardening" card for those.</div>`,
  },

  /* ------------------------------------------------------------------ */
  kAlas: {
    baslik: 'Steels and alloying elements',
    html: `
<p>A steel's behavior is set by its carbon content together with its alloying elements. This card does two things: it lets you pick a
steel from the library, and it lets you enter and save your own composition.</p>
<h4>The library and nominal compositions</h4>
<p>Standards (EN, ISO, SAE) specify a <b>range</b> for each element — for 42CrMo4, for example, C 0.38–0.45%. The calculation uses the
middle of that range. Where the standard only gives a maximum ("Si ≤ 0.40"), a typical value is used. An actual heat can fall anywhere
in the range; entering the values from your mill certificate and saving them gives the most accurate result.</p>
<h4>Austenite and ferrite stabilizers</h4>
<p><b>γ-formers</b> (austenite stabilizers: C, Mn, Ni, Cu, N) expand the austenite (γ) field and lower A1 and A3.
<b>α-formers</b> (ferrite stabilizers: Si, Cr, Mo, V, W, Ti, Nb) expand the ferrite (α) field and raise A1.
Almost every alloying element shifts the eutectoid point to lower carbon, which is why an alloy steel with 0.6% C can already behave
as eutectoid or even hypereutectoid.</p>
<h4>Effects of the elements</h4>
<table>
  <tr><th>Element</th><th>Phase</th><th>Hardenability</th><th>Carbide</th><th>Main effect</th></tr>
  <tr><td><b>C</b></td><td>γ</td><td>increases</td><td>Fe₃C</td><td>Sets martensite hardness; lowers Ms more than any other element</td></tr>
  <tr><td><b>Mn</b></td><td>γ</td><td>strong increase</td><td>weak</td><td>Ties up sulfur as MnS; in excess, promotes retained austenite and grain growth</td></tr>
  <tr><td><b>Si</b></td><td>α</td><td>moderate</td><td>none</td><td>Deoxidizer; strengthens ferrite; retards cementite formation (spring steels)</td></tr>
  <tr><td><b>Cr</b></td><td>α</td><td>strong increase</td><td>M₇C₃, M₂₃C₆</td><td>Wear and tempering resistance; stainless above ~12%</td></tr>
  <tr><td><b>Ni</b></td><td>γ</td><td>moderate</td><td>none</td><td>Improves toughness, especially at low temperature</td></tr>
  <tr><td><b>Mo</b></td><td>α</td><td>very strong</td><td>M₂C, M₆C</td><td>Reduces temper embrittlement; elevated-temperature strength; effective even in small amounts</td></tr>
  <tr><td><b>V</b></td><td>α</td><td>increases if dissolved</td><td>MC (VC)</td><td>Grain refinement; very stable carbide, secondary hardening</td></tr>
  <tr><td><b>W</b></td><td>α</td><td>moderate</td><td>M₆C</td><td>Hot hardness (tool steels)</td></tr>
  <tr><td><b>Cu</b></td><td>γ</td><td>slight</td><td>none</td><td>Atmospheric corrosion resistance; in excess, hot shortness during hot working</td></tr>
</table>
<p class="not-satir">Carbide formers (Cr, Mo, V, W) tie up part of the carbon as carbides. Carbides that do not dissolve at the austenitizing
temperature pin the grain boundaries but also lower the carbon in the austenite — and with it the hardenability.</p>
<h4>Calculated vs. empirical</h4>
<p>When <b>Calculated</b> (CALPHAD isopleth) is ticked and a calculation exists for this alloy ("● calc" in the list), the diagram switches to
that steel's thermodynamic isopleth, with carbides shown as separate phases. Otherwise the <b>empirical model</b> is used: the binary
Fe–C boundaries are shifted with the alloy coefficients from Andrews' (1965) equations.</p>
<h4>Saving</h4>
<p>You can save a composition you entered under a name. Saved steels appear in orange at the top of the search list and are stored in this
browser. If a saved composition has the same alloy content as one with a calculated isopleth, the calculated diagram opens automatically.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kIslem: {
    baslik: 'Heat-treatment temperatures',
    html: `
<p>Heat treatment means heating a steel to a given temperature, holding it there and cooling it at a given rate. The temperature is
chosen relative to the critical lines of the phase diagram; this card calculates the windows for the selected carbon content and draws
them on the diagram.</p>
<table>
  <tr><th>Process</th><th>Temperature</th><th>Cooling</th><th>Purpose / result</th></tr>
  <tr><td><b>Full annealing</b></td><td>Hypo: A3 + 30–50 °C<br>Hyper: A1 + 30–50 °C</td><td>In the furnace, very slow</td><td>Softest condition; coarse pearlite. Machinability, relief of internal stresses</td></tr>
  <tr><td><b>Normalizing</b></td><td>Hypo: A3 + 50–70 °C<br>Hyper: Acm + 50–70 °C</td><td>Still air</td><td>Grain refinement and homogenization; fine pearlite. Standard treatment after casting and forging</td></tr>
  <tr><td><b>Hardening</b></td><td>Hypo: A3 + 30–50 °C<br>Hyper: A1 + 30–50 °C</td><td>Water / oil (fast)</td><td>Martensite; maximum hardness. Must be followed by <b>tempering</b></td></tr>
  <tr><td><b>Spheroidizing</b></td><td>Just below A1 (or cycling around A1)</td><td>Slow</td><td>Cementite spheroidizes; best formability, preparation of hypereutectoid steels for hardening</td></tr>
  <tr><td><b>Stress relieving</b></td><td>550–650 °C (below A1)</td><td>Slow</td><td>Reduces stresses from welding, machining or cold forming without any phase change</td></tr>
</table>
<h4>Why do hypo- and hypereutectoid steels differ?</h4>
<p>In a <b>hypoeutectoid</b> steel (less carbon than the eutectoid), heating below A3 leaves some ferrite untransformed; on quenching it
remains as soft spots. A <b>hypereutectoid</b> steel, however, is hardened from <b>A1 + 30–50 °C</b>, not from above Acm:</p>
<ul>
  <li>Above Acm all the cementite dissolves, the austenite picks up more carbon → Ms drops and <b>retained austenite</b> increases.</li>
  <li>The higher temperature causes <b>grain coarsening</b> and increases the risk of <b>quench cracking and distortion</b>.</li>
  <li>The fine, undissolved cementite particles contribute to <b>wear resistance</b> (e.g. 100Cr6 bearing steel).</li>
</ul>
<h4>Why "+30–50 °C"?</h4>
<p>Transformation takes time, the core of a part heats up later than the surface, and furnaces and thermocouples have tolerances. Going
higher brings grain growth, surface decarburization and scaling. A common shop rule for soaking time is <b>about 1 hour per 25 mm of
section</b> (it varies with material, furnace and process).</p>
<h4>Ae, Ac and Ar</h4>
<p>The lines on the diagram are <b>equilibrium</b> temperatures (Ae). On heating the transformation occurs somewhat higher (<b>Ac</b>, from
French <i>chauffage</i>, heating) and on cooling somewhat lower (<b>Ar</b>, <i>refroidissement</i>, cooling). The gap grows with the
heating or cooling rate. Values in supplier data sheets are usually Ac temperatures and lie a few to a few tens of degrees higher.</p>
<h4>Windows on a calculated isopleth</h4>
<p>In an alloy isopleth A1 is not a single line but a three-phase band between Ae1 (austenite starts to form) and the temperature at which
ferrite disappears. The windows are drawn from these calculated boundaries. For steels with carbide formers (Cr, Mo, V), supplier tables
usually recommend somewhat higher temperatures so that the carbides dissolve sufficiently (e.g. 42CrMo4 hardening at 820–860 °C). The
steel's data sheet always takes precedence.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kSogu: {
    baslik: 'Cooling and hardening',
    html: `
<p>After austenitizing, the <b>cooling rate</b> decides what the austenite transforms into. The phase diagram only covers very slow
(equilibrium) cooling; on fast cooling diffusion cannot keep up and non-equilibrium structures form.</p>
<table>
  <tr><th>Structure</th><th>Forms when</th><th>Properties</th></tr>
  <tr><td><b>Coarse pearlite</b></td><td>Slow furnace cooling (transformation around 700 °C)</td><td>Soft, easy to machine</td></tr>
  <tr><td><b>Fine pearlite</b></td><td>Air cooling (normalizing)</td><td>Stronger and tougher</td></tr>
  <tr><td><b>Bainite</b></td><td>Intermediate rates / isothermal hold at ~250–550 °C</td><td>Good balance of strength and toughness</td></tr>
  <tr><td><b>Martensite</b></td><td>Fast quench below Ms (water, oil)</td><td>Very hard and brittle; tempering is essential</td></tr>
</table>
<h4>Martensite, Ms and Mf</h4>
<p>Martensite forms by a diffusionless shear transformation: carbon is trapped in the iron lattice and distorts it, which is where the
hardness comes from. The transformation starts at <b>Ms</b>, proceeds as the temperature falls and finishes at <b>Mf</b>. Carbon and the
alloying elements lower Ms; here Andrews' equation is used:</p>
<div class="formul">Ms (°C) = 539 − 423·C − 30.4·Mn − 17.7·Ni − 12.1·Cr − 7.5·Mo − 7.5·Si</div>
<h4>Retained austenite</h4>
<p>If Mf lies below room temperature the transformation cannot finish and some austenite remains untransformed. Its amount is estimated
with the Koistinen–Marburger relation:</p>
<div class="formul">martensite fraction = 1 − exp[−0.011·(Ms − T)]</div>
<p>Retained austenite causes dimensional instability and loss of hardness; where necessary it is transformed by a <b>sub-zero treatment</b>
(−80 °C or lower). It is significant in high-carbon steels (e.g. 1% C).</p>
<h4>Hardness vs. hardenability</h4>
<ul>
  <li><b>Hardness</b>: how hard does fully martensitic steel get? It depends almost entirely on <b>carbon</b> (Hodge–Orehoski). Above about
  0.6% C it barely increases further (~64–66 HRC) because of retained austenite.</li>
  <li><b>Hardenability</b>: how <b>deep</b> does martensite form? This is set by the alloying elements. Its measure is the <b>ideal critical
  diameter D<sub>I</sub></b>: the diameter of a bar that would have 50% martensite at its center under an infinitely severe quench. Here it is
  calculated with the ASTM A255 multiplying factors; in practice it is measured with the Jominy end-quench test.</li>
</ul>
<h4>Quench severity</h4>
<p>Approximate Grossmann H values: still air ~0.02 · still oil ~0.3 · agitated oil ~0.5–0.8 · still water ~1 · agitated water ~1.5–2 ·
brine ~2–5. The more severe the quench, the thicker the section that hardens — but the greater the risk of cracking and distortion. That
is why high-hardenability alloy steels are quenched in oil and plain carbon steels in water.</p>
<div class="ozet">The predicted structure on the card is a rough guide for a ~25 mm section. The actual result depends on part thickness and on
the steel's CCT (continuous cooling transformation) diagram.</div>`,
  },

  /* ------------------------------------------------------------------ */
  kBolge: {
    baslik: 'Selected point: phases and fields',
    html: `
<p>A <b>phase</b> is a region of the material with uniform chemical composition and crystal structure, separated from other regions by
boundaries. This card tells you which phases coexist at the selected point.</p>
<h4>Phases in the Fe–C system</h4>
<table>
  <tr><th>Phase</th><th>Crystal</th><th>Max. C</th><th>Notes</th></tr>
  <tr><td><b>α-ferrite</b></td><td>BCC</td><td>~0.02% (at 727 °C)</td><td>Soft, ductile, ferromagnetic below 770 °C</td></tr>
  <tr><td><b>γ-austenite</b></td><td>FCC</td><td>~2.1% (at 1148 °C)</td><td>Starting phase for heat treatment; non-magnetic</td></tr>
  <tr><td><b>δ-ferrite</b></td><td>BCC</td><td>~0.09%</td><td>Only at very high temperature; important in casting and welding</td></tr>
  <tr><td><b>Cementite Fe₃C</b></td><td>orthorhombic</td><td>6.69% (fixed)</td><td>A very hard, brittle carbide</td></tr>
  <tr><td><b>Liquid (L)</b></td><td>—</td><td>—</td><td>Melt</td></tr>
</table>
<p class="not-satir">This application's calculation gives slightly different numbers from textbook values (e.g. maximum carbon in austenite 2.05%,
eutectic 4.38%). The textbook 2.14% and 4.3% come from older experimental compilations; the calculation is based on a current
thermodynamic assessment.</p>
<h4>Gibbs phase rule</h4>
<p>At constant pressure <b>F = C − P + 1</b> (F: degrees of freedom, C: number of components, P: number of phases). For binary Fe–C (C = 2):</p>
<ul>
  <li><b>Single-phase field</b> (F = 2): temperature and composition can be varied independently.</li>
  <li><b>Two-phase field</b> (F = 1): once the temperature is fixed, the compositions of both phases are fixed (the ends of the tie-line).</li>
  <li><b>Three phases</b> (F = 0): possible only at one temperature; these are the eutectoid, eutectic and peritectic lines.</li>
</ul>
<h4>In an alloy isopleth</h4>
<p>With more components in an alloy steel, the phase rule allows more phases to coexist. That is why <b>three- and four-phase fields</b>
(e.g. γ + α + M₂₃C₆) cover large areas of an isopleth and A1 becomes a band rather than a line. Alloy carbides (M₇C₃, M₂₃C₆, M₆C, MC) appear
as separate phases; M stands for a mixture of metal atoms (Fe, Cr, Mo, V…).</p>`,
  },

  /* ------------------------------------------------------------------ */
  kOran: {
    baslik: 'Phase fractions and the lever rule',
    html: `
<p>In a two-phase field you need to know not only <b>which</b> phases are present but also <b>how much</b> of each. This card gives the weight
fraction of each phase and that phase's own carbon content.</p>
<h4>The lever rule</h4>
<p>Draw a horizontal line (the tie-line) at the selected temperature; where it meets the boundaries of the two-phase field are the
compositions of the phases: <b>C<sub>α</sub></b> (left) and <b>C<sub>β</sub></b> (right). Conservation of carbon gives:</p>
<div class="formul">W<sub>α</sub> = (C<sub>β</sub> − C₀) / (C<sub>β</sub> − C<sub>α</sub>)  ·  W<sub>β</sub> = (C₀ − C<sub>α</sub>) / (C<sub>β</sub> − C<sub>α</sub>)</div>
<p>C₀ is the carbon content of the steel. The rule takes its name from a seesaw: the <b>farther</b> a phase lies from the overall
composition, the <b>less</b> of it there is.</p>
<p><b>Example</b> (from this application's calculation): a 0.30% C steel at 780 °C is in the α + γ field. At this temperature the ferrite holds
0.014% C and the austenite 0.435% C. Ferrite fraction = (0.435 − 0.30) / (0.435 − 0.014) ≈ <b>32%</b>, austenite ≈ <b>68%</b>.</p>
<h4>By weight or by volume?</h4>
<p>The calculation is by weight. Metallography measures area (≈ volume) fractions in the image. Since ferrite and cementite have similar
densities (7.87 and ~7.7 g/cm³), the difference is small for steels.</p>
<h4>In an alloy isopleth</h4>
<p>In a multicomponent steel the tie-lines do not lie in the plane of the isopleth (the phases partition the alloying elements as well as the
carbon). The lever rule therefore <b>cannot</b> be applied to an isopleth; the fractions are taken directly from the thermodynamic calculation
and marked "calculated" on the card.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kKritik: {
    baslik: 'Critical temperatures and transformations',
    html: `
<p>The temperatures at which phase changes occur when a steel of the selected carbon content is heated are its <b>critical
temperatures</b>. Heat-treatment temperatures are chosen relative to them.</p>
<table>
  <tr><th>Symbol</th><th>Meaning</th></tr>
  <tr><td><b>A1</b></td><td>Eutectoid temperature (~727 °C). Below it ferrite + cementite; above it austenite starts to form.</td></tr>
  <tr><td><b>A3</b></td><td>In a hypoeutectoid steel, the temperature at which ferrite fully transforms to austenite. It falls with increasing carbon.</td></tr>
  <tr><td><b>Acm</b></td><td>In a hypereutectoid steel, the temperature at which cementite fully dissolves in austenite. It rises steeply with carbon.</td></tr>
  <tr><td><b>A2</b></td><td>Curie temperature (~770 °C): ferrite loses its magnetism. It is not a phase change, so it is not shown as a line.</td></tr>
  <tr><td><b>Solidus / liquidus</b></td><td>Start / end of melting. The pouring temperature is chosen above the liquidus.</td></tr>
</table>
<h4>Invariant reactions</h4>
<ul>
  <li><b>Eutectoid</b> (~727 °C, ~0.76% C): γ → α + Fe₃C. The product is <b>pearlite</b> (fine lamellae of ferrite and cementite).</li>
  <li><b>Eutectic</b> (~1148 °C, ~4.3% C): L → γ + Fe₃C. The product is <b>ledeburite</b>, the structure of white cast iron.</li>
  <li><b>Peritectic</b> (~1495 °C, ~0.17% C): δ + L → γ. Important in the solidification and welding of low-carbon steels.</li>
</ul>
<h4>Ac, Ae, Ar</h4>
<p>The values are equilibrium temperatures (Ae). In real heating the transformation occurs somewhat higher (Ac) and in cooling somewhat lower
(Ar). See the "Heat-treatment temperatures" info window for details.</p>
<h4>In an alloy isopleth: Ae1, Ae3, Aecm</h4>
<p>In an alloy steel the eutectoid transformation takes place over a temperature <b>range</b>. <b>Ae1</b>: austenite first appears. <b>Ae3</b>:
ferrite disappears (in hypereutectoid steels, the "top of the A1 band"). <b>Aecm</b>: the last carbide dissolves. The list also shows at which
temperature each carbide dissolves or transforms into another. Very stable MC carbides (such as VC) can persist to very high temperatures;
since they are deliberately left undissolved as grain refiners, they are not counted in Aecm.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kYatay: {
    baslik: 'Isotherm: boundaries at one temperature',
    html: `
<p>The horizontal line across the diagram at the selected temperature is an <b>isotherm</b>. This card lists which field you are in along
that line for each range of carbon content; the field of the selected point is highlighted.</p>
<h4>What is it good for?</h4>
<ul>
  <li>It gives the <b>maximum carbon austenite can dissolve</b> at a given furnace temperature (the right-hand boundary of the austenite field,
  i.e. the Acm curve). This sets the upper limit of surface carbon in carburizing and tells you how much carbide stays undissolved in a
  hypereutectoid steel.</li>
  <li>The ends of a two-phase field are the <b>carbon contents of the two phases</b> at that temperature; the lever rule uses exactly these two numbers.</li>
  <li>You can see at a glance how steels with different carbon contents behave at the same furnace temperature.</li>
</ul>
<h4>In an alloy isopleth</h4>
<p>On an isopleth the field boundaries are <b>not</b> the carbon contents of the phases; they only show which combination of phases this
steel (with these alloy contents) has at each carbon content.</p>`,
  },

  /* ------------------------------------------------------------------ */
  kYapi: {
    baslik: 'Microstructure after slow cooling',
    html: `
<p>Estimates the room-temperature microstructure when the steel is cooled slowly (close to equilibrium) from the austenite field. The
fractions are calculated with the lever rule just below A1.</p>
<h4>Constituents</h4>
<ul>
  <li><b>Proeutectoid ferrite</b>: in hypoeutectoid steels, ferrite that forms between A3 and A1, <i>before</i> the eutectoid reaction; light grains
  along the prior austenite grain boundaries.</li>
  <li><b>Proeutectoid (secondary) cementite</b>: in hypereutectoid steels, a cementite network that forms on the grain boundaries between Acm and
  A1. It causes brittleness and is removed by spheroidizing.</li>
  <li><b>Pearlite</b>: the lamellar α + Fe₃C formed when the remaining austenite transforms eutectoidally at A1. On its own it is roughly
  <b>89% ferrite and 11% cementite</b>.</li>
  <li><b>Ledeburite</b> (cast iron): the eutectic product; on further cooling its austenite also transforms to pearlite ("transformed ledeburite").</li>
</ul>
<h4>Estimating carbon from the microstructure</h4>
<p>This also works in reverse: if you measure the pearlite fraction in a slowly cooled hypoeutectoid steel, the carbon content is roughly
<b>%C ≈ pearlite fraction × 0.76</b> (e.g. half pearlite ≈ 0.38% C). It is a practical way to identify an unknown part quickly.</p>
<h4>In an alloy isopleth</h4>
<p>The card shows the equilibrium phases a little below the A1 band: ferrite, cementite and alloy carbides. Which carbide actually forms depends
on cooling rate and time; the equilibrium calculation gives an upper bound and a direction.</p>`,
  },

  /* ------------------------------------------------------------------ */
  yontem: {
    baslik: 'Methods and sources',
    html: `
<h4>Binary Fe–C diagram</h4>
<p>The boundaries are calculated by Gibbs energy minimization with <b>pycalphad</b> (an open-source CALPHAD library). Database: the Fe–C assessment
by <b>Fei &amp; Brosh (2014)</b> (<code>cfe_broshe.tdb</code>). Phases: BCC_A2, FCC_A1, CEMENTITE, LIQUID; graphite is excluded to obtain the
metastable Fe–Fe₃C diagram. The range 400–1600 °C is scanned in 1 °C steps; two-phase boundaries are taken from the tie-line end points and the
invariant points are located to within 0.01 °C.</p>
<h4>Alloy steel isopleths (calculated)</h4>
<p>The <b>MatCalc open steel database</b> mc_fe v2.062 (TU Wien, Open Database License) is used with pycalphad. For each steel the alloying elements
are held constant and a vertical section (isopleth) is calculated for 0–1.8% C and 550–1100 °C. Phase fractions are by weight; the carbon content
of each phase comes directly from the calculation. Validation: the Ae1/Ae3/Aecm values for C45, 42CrMo4, 16MnCr5 and 100Cr6 agree with measured Ac
values in the literature.</p>
<h4>Empirical relations</h4>
<ul>
  <li>Effect of alloying on A1/A3: K. W. Andrews, <i>J. Iron Steel Inst.</i> 203 (1965) — the alloy coefficients are added to the calculated binary curves.</li>
  <li>Shift of the eutectoid carbon: approximate slopes read from the Bain diagram.</li>
  <li>Ms: Andrews (1965) linear equation. Retained austenite: Koistinen &amp; Marburger (1959).</li>
  <li>As-quenched hardness: Hodge &amp; Orehoski (1946). Hardenability: ASTM A255 (Grossmann D<sub>I</sub>), grain size 7.</li>
</ul>
<h4>Steel library</h4>
<p>63 low-alloy steels; composition ranges from EN ISO 683-1/-2/-3/-17, EN 10025-2, EN 10083, EN 10085, EN 10089, EN 10132, ISO 4957, EN 10213 and
EN 10293, with the nominal value taken as the middle of the range. P, S, B, Al, N, Nb and Ti are not included in the model.</p>
<h4>Limitations</h4>
<ul>
  <li>All diagram values are <b>equilibrium</b> values; real heating and cooling deviate depending on rate.</li>
  <li>Stainless and high-alloy tool steels (sigma and Laves phases) are outside the current scope.</li>
  <li>Predicted cooling structures are rough; for definitive results use the steel's CCT diagram and the supplier's data sheet.</li>
</ul>
<h4>References</h4>
<ul>
  <li>pycalphad — R. Otis &amp; Z.-K. Liu, <i>J. Open Res. Softw.</i> 5 (2017) 1 (MIT license).</li>
  <li>Fe–C assessment — Fei &amp; Brosh (2014), <code>cfe_broshe.tdb</code>.</li>
  <li>The alloy steel isopleths are produced from the MatCalc mc_fe v2.062 database by E. Povoden-Karadeniz and A. Jacob (TU Wien), which is made
  available under the <b>Open Database License (ODbL)</b>.</li>
</ul>
<div class="ozet">Faz Atlası is intended for education and preliminary design. Temperatures used in production must be confirmed against the mill certificate
and the supplier's data.</div>
<p class="not-satir">Faz Atlası v1.0 · 63 steels, 52 calculated isopleths · open source</p>`,
  },
};
