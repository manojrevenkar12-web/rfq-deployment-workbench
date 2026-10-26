# Console design

Audience: deployment strategists and the customer's sales engineering leads, on a laptop in a meeting
room or a phone on the train back. The console has one job: make the customer's own numbers easy to say
out loud.

- **Palette.** Drafting-film paper (#EEF1EE) and graphite ink (#16202A). Signals are the RAL traffic
  colours the customers' shop floors already read: 5017 traffic blue for action and work, 6024 green,
  1003 signal yellow, 3020 red. Colour never carries meaning alone: every swatch has a word.
- **Type.** Archivo with its width axis: the customer's name runs wide and heavy (the one loud thing on a
  page), tables run slightly narrow, figures are tabular. Source Serif 4 is used only for the buyer's own
  words, so a quoted requirement never reads like the agents' analysis.
- **One signature.** The lead-time strip: the average tender's days, working solid, waiting for a
  colleague hatched like a section cut on a drawing, waiting on the buyer hatched in signal yellow. It
  draws once on load and resizes when the scope changes; nothing else on the page moves unasked.
- **States.** Every view: a skeleton shaped like its content, an error that says what failed with a retry
  (or a token prompt), an empty state that says what to hand over.
- **Tokens.** `web/src/shared/theme/tokens.css` (colours, type scale, spacing, radii, durations) and
  `tokens.ts` (words and tones for states, motion numbers for Framer Motion). Components carry no numbers
  of their own.
