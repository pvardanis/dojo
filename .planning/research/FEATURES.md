# Feature Research

**Domain:** Local/offline LLM-powered flashcard + study app (MLOps interview prep; single-user; localhost; markdown notes + Q&A drill)
**Researched:** 2026-04-18
**Confidence:** MEDIUM

> **Sourcing note.** External web tools (WebSearch, Brave, Exa, Firecrawl,
> Context7) were unavailable to this research run (`.planning/config.json`
> has `brave_search`, `firecrawl`, `exa_search` all `false`, and
> `WebSearch` was denied by the sandbox). Findings below are drawn from
> training-data knowledge of the flashcard / study-app ecosystem
> (Anki, Mnemosyne, SuperMemo, Quizlet, RemNote, Obsidian-Spaced-Repetition,
> Mochi, Orbit, Brainscape, Duolingo-style pattern, plus LLM-powered
> entrants: Wisdolia, Quizgecko, StudySmarter, Monic.ai, Studdy Buddy,
> ChatGPT-as-flashcard-generator workflows, and the broader "chat-with-PDF"
> wave). Where a claim depends on product-specific details that may have
> shifted since training, it is marked **LOW** confidence. Where a claim
> is about the shape of the category itself (what an SRS is, what users
> expect), it is **HIGH** confidence because the pattern is old and
> well-documented. Anything that feels like it needs to be re-checked
> before a product decision rides on it is called out inline.

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features a user picking up *any* flashcard / study app in 2026 expects
to find. Missing any of these makes the product feel incomplete or
broken for its category — even in an interview-prep, single-user,
local niche.

| Feature | Why Expected | Complexity | Dojo Status | Notes |
|---|---|---|---|---|
| **Create Q&A cards (question + answer)** | Defines the category | LOW | **MVP** | Covered (`Card.question`, `Card.answer`). |
| **Edit cards after creation** | Cards are rarely right first time; LLM-generated cards *especially* | LOW | **MVP** (review step) | Dojo edits during review draft. Confirm post-save edit is in MVP — see Gap #1. |
| **Delete cards** | Cards go stale or get duplicated on regenerate | LOW | **Partial** | Reject-in-review covered; post-save delete not explicitly in PROJECT.md — see Gap #1. |
| **Reveal-answer interaction (hidden until user chooses)** | Core of self-testing / active recall | LOW | **MVP** | Space reveals. HIGH confidence this is universal. |
| **Binary or graded self-rating** | How the app learns whether you knew it | LOW | **MVP** | ← wrong / → right. Anki uses 4 (Again/Hard/Good/Easy); Quizlet/Brainscape use variants. Binary is fine for MVP *because* no SRS yet; Phase 3 SRS may want finer grain (see Pitfall #1 in PITFALLS.md). |
| **Persistent card storage across sessions** | Obviously | LOW | **MVP** | SQLite + Alembic. |
| **Review history / "I've seen this card before" signal** | Users want to know what they've drilled, even pre-SRS | LOW | **MVP** | Append-only `CardReview` log. |
| **Organize cards (decks / tags / filters)** | Users expect to drill "just k8s" without wading through everything | LOW | **MVP** | Free-form tags + source filter. HIGH confidence this is a universal expectation. |
| **Render rich text in answers (at minimum: markdown + code blocks)** | MLOps-domain cards *will* contain code — `kubectl apply -f ...`, Python snippets, YAML | LOW-MED | **Implicit?** | Notes render via `markdown-it-py`. **Gap #2**: PROJECT.md doesn't explicitly say card questions/answers render markdown in drill view. This is table stakes for a technical-domain study app. See Gap #2. |
| **See your notes / source material separately from drilling** | Reading ≠ drilling; both modes needed | LOW | **MVP** | Source-detail page covered. |
| **Session summary at end of drill** | "Did I pass? What did I miss?" | LOW | **MVP** | Spec §5.2: X/Y correct + duration. |
| **Shuffle / random order** | Otherwise users memorize position, not content | LOW | **MVP** | Spec §5.2 says "cards (random order)". |
| **Reasonable drill-length control** | All cards in one sitting doesn't scale past ~50 cards | LOW | **Partial** | Source/tag filter gives *some* control. No explicit "deck size cap" or "session of N cards" — see Gap #3. |
| **Keyboard-driven drill** | Speed-drillers hate clicking | LOW | **MVP** | Space / ← / →. |
| **Don't lose my work on crash / close** | Basic trust | LOW-MED | **Covered with tradeoff** | Drafts are *deliberately* in-memory and lost on restart (spec §5.1). Acceptable for single-user local if communicated, but friction if you close the tab mid-review. Noted as tradeoff, not a gap. |

**Dojo table-stakes verdict:** strong coverage. Three gaps flagged for
requirements review below (Gaps #1, #2, #3).

---

### Differentiators (Competitive Advantage)

Features that would set Dojo apart from generic flashcard apps in the
MLOps-interview-prep niche. Not required; choose one or two to lean on.

| Feature | Value Proposition | Complexity | Dojo Status | Notes |
|---|---|---|---|---|
| **Generate cards from *my own* source material (file / URL / topic)** | The #1 reason to build this vs use Anki: Anki makes you author cards, AI-study apps make you upload a PDF and take what you get | MED | **MVP core** | Three ingestion modes is differentiated. HIGH confidence most competitors lock you into *either* hand-authoring *or* LLM-from-upload, rarely both with topic-prompt-alone. |
| **User prompt shapes every generation** ("basic intro to k8s, skip RBAC") | Most AI-study apps generate generically from the doc; shaping the *output* to the user's current knowledge gap is rare | LOW (once ingestion works) | **MVP** | Differentiator. Spec §1 and §5.1. |
| **Review-before-persist** (edit / reject before save) | Most "AI generates cards" apps dump everything into your library; Dojo's human-in-the-loop is rarer and better | MED | **MVP** | Differentiator. Draft store + atomic save. |
| **Local-first / localhost-only** | Privacy, no subscription, study material stays on disk | LOW (it's the default architecture) | **MVP** | Differentiator versus Quizlet/RemNote/StudySmarter (cloud SaaS). Comparable to Anki + AnkiConnect plugins. |
| **Provider-swappable LLM (port)** | User can move from paid API to local model without rebuild | LOW-MED | **MVP (port designed)** | Phase 4 swap. Differentiates from apps hard-wired to OpenAI/Anthropic. |
| **Source → Note → Cards linked model** (not just decks) | Traceability: "where did this card come from?" is valuable when you're prepping from specific docs | LOW | **MVP** | Domain model has it. Differentiator versus deck-of-cards-only apps. |
| **Dating-app drill interaction** (Space + arrows + slide-off) | Tactile, fast, enjoyable | LOW | **MVP** | Differentiator in *feel*, not capability. HIGH confidence this is rare on desktop flashcard apps. |
| **Reproducible generation** (source_text + user_prompt stored) | Rare in LLM-powered apps; most don't store the prompt | LOW | **MVP** | `Source.source_text` + `Source.user_prompt` stored. Useful for Phase 4 evals. |
| **MLOps-curated content spine** (Black Lodge wiki) | Users get a *studyable corpus* out of the box, not a blank deck | LOW (already exists) | **MVP** | Differentiator — gives the app a first-day purpose beyond "import something." |
| **RAG over a folder of notes** (Phase 2) | "Study from everything I know about X" is a strong pitch | HIGH | **Phase 2** | Differentiator if execution is good; pitfall if retrieval quality is bad (see PITFALLS.md). |
| **Mock-interview typed-answer mode with LLM grading** (Phase 2) | The *actual* interview-prep killer feature. Drill ≠ interview. | HIGH | **Phase 2** | Arguably the biggest differentiator for the stated domain. See Phase-2 note below. |
| **SRS scheduling** (Phase 3) | Anki has it; most LLM-study apps don't | MED | **Phase 3** | Not a differentiator versus Anki, but a differentiator versus LLM-study-app peers. HIGH confidence. |
| **Semantic search across notes + cards** (Phase 4+) | "What did I study about X?" | MED | **Phase 4+** | Differentiator. Less critical once RAG exists (Phase 2 infra reusable). |

**Recommended differentiator lean:** MVP should lean on _generate-from-source-with-user-prompt + review-before-persist + local-first_.
Phase 2's **mock-interview mode** is the long-term differentiator given
the MLOps-interview framing — treat Phase 1 as the path that makes
Phase 2 credible.

---

### Anti-Features (Commonly Requested, Often Problematic)

Features that pattern-match to "good idea" but either don't fit Dojo's
single-user local-first frame or become scope-creep traps. Dojo's spec
(§11 Intentional exclusions + Out of Scope in PROJECT.md) already names
most of these — this section extends the list with ones *not* yet
explicitly called out, and agrees with the ones that are.

| Anti-Feature | Why Requested | Why Problematic for Dojo | Alternative |
|---|---|---|---|
| **"Generate-and-save" (no review step)** | Faster, "lets me study more cards" | LLM cards are noisy; unreviewed cards pollute the deck and erode trust in the whole system | Keep review-before-persist as a hard rule. Already in MVP. |
| **Multiple LLM providers shipped simultaneously in MVP** | "Give users choice" | Port abstractions built without a second concrete implementation leak; doubles prompt-tuning work; doubles cost of error-handling tests | Already Phase 4. Agreed. (Spec §9.) |
| **Shipping Ollama / local-LLM support in MVP** | "Privacy / no API costs" | Local models in early 2026 still produce noticeably worse structured output than frontier APIs — tuning prompts *and* debugging local-model quirks *and* shipping the app is three projects at once | Phase 4. Agreed. The port makes it cheap later. |
| **Real-time collaborative decks / sharing** | Social-learning vibes | Single-user local by design; adds auth, sync, conflict resolution | Already excluded. Agreed. |
| **Account system / "cloud sync" across devices** | Users expect it from web apps | Single-user localhost — adding this is basically a second product | Already excluded. Agreed. |
| **Spaced repetition in MVP** | "Anki has it, we should too" | SRS needs a scheduler, a due-queue, and a different drill-start UX ("pick due cards" replaces "pick deck"). Shipping it half-baked is worse than not shipping. | Phase 3 with CardReview log already in MVP for backfill. Agreed. (Spec §9.) |
| **Rich-text / WYSIWYG card editor** | Users want to paste images, color text | Forces you to solve sanitization, content-type limits, storage — for a code-and-markdown domain where plain markdown is ideal | Markdown-only in textareas. Spec already implies this; pin it as a decision. |
| **Image-in-cards / LaTeX-in-cards** | "My domain has diagrams / equations" | MLOps interview prep is almost entirely code + prose + architecture *descriptions*. LaTeX adds KaTeX/MathJax dep; images add storage/CDN decisions. 80/20 says not now. | Defer to Phase 4+. Markdown code blocks and ASCII/Mermaid in markdown covers 90% of actual needs. |
| **Audio / TTS of cards** | Accessibility pitch | Doesn't fit "sit at a laptop and drill between tabs." Real accessibility story is keyboard nav, which you already have. | Out of scope indefinitely. |
| **"AI tutor" open-ended chat mode** | Obvious LLM-wrapper temptation | Different product. Blurs Dojo's purpose ("generate → drill"). An open chat surface is also a cost and safety surface. | Out of scope. Phase 2 mock-interview is the constrained, purpose-shaped version of this urge. |
| **Gamification: XP, levels, badges, streaks in MVP** | Duolingo envy | Streaks/heatmaps are cheap (derivable from CardReview); XP/levels/badges add UI and state without clear value for an adult interview-prep user | Streaks/heatmaps → Phase 3. XP/levels/badges → no. |
| **Leaderboards / social streaks** | Gamification cliché | Single-user local; requires accounts | Out of scope. |
| **"AI improves your card" / auto-rewriting after creation** | Continuous-improvement pitch | Undermines the review-before-persist trust model; produces subtle drift users didn't approve | Keep regeneration explicit and user-initiated. Card edits are manual. |
| **Auto-categorize / auto-tag cards with LLM** | "Save me tagging" | In single-user app over a 100-500-card library, free-form user tags are fast and correct; LLM-inferred tags drift across sessions, fragment the vocabulary, and silently change meaning | Keep free-form tags user-driven. Default-copy from source (already in MVP) covers the lazy path. |
| **Card versioning / full history** | "What if I want to see the old question?" | Spec already excludes (§11). Adds schema weight, UI decisions, little real use | Out of scope. Append-only CardReview already gives the signal that matters. |
| **PDF ingestion in MVP** | "My study material is in PDFs" | PDF extraction is a wrapper-of-wrappers (pypdf/pdfminer/unstructured/OCR fallback). Each has failure modes and test burden | Phase 2 or later. MVP's FILE kind covers `.md` and pasted text — most MLOps wiki sources. |
| **YouTube / transcript ingestion in MVP** | "AI-study apps all do this" | Transcript APIs change; Whisper adds a heavy dep; accuracy on technical talks is uneven | Phase 2+. URL kind covers text-first web pages, which is the bulk of study material. |
| **Multi-select bulk edit in card-review UI** | Power-user pitch | HTMX + batch-state in templates is a non-trivial UX piece; card-by-card approval matches the single-user scale | Defer; one-by-one is fine at MVP scale. Revisit if decks routinely >50 cards. |
| **Import from Anki / Quizlet / CSV in MVP** | "Bring my existing decks" | Dojo's value is *generating new* cards, not migrating. Adds parser code and schema-mapping decisions | Phase 4+ if earned. Agreed; not in spec. |
| **Export to Anki in MVP** | Hedging against Dojo | Already Phase 4+. Agreed. |
| **Full-text search in MVP** | Power-user feature | Card/deck scale is small in first weeks; source+tag filter covers 80% | Phase 4+. Agreed. |
| **In-app prompt editor for users to tune generation prompts** | "Let users customize" | Opens a huge support/debugging surface; generation quality becomes user's fault; versioning problem | Keep prompts in code (Jinja templates, spec §4.1). User shapes via `user_prompt`, not template edits. |
| **Analytics dashboards in MVP** | "I want to see my progress" | Streaks and session summary cover this. Full dashboards = Phase 3 | Session summary at end of drill. Richer views Phase 3. Agreed. |
| **Undo on drill rating** | "I hit the wrong arrow" | Append-only review log is a design choice; allowing undo leaks complexity into the log and the UI | Live with it. If it matters, add a 5-second "undo" toast (client-side only, deletes the last review row). Out of MVP. |
| **"Continue where I left off" on a drill session** | Quality-of-life | Drill sessions in spec are ephemeral (no Session entity). Adding one is a small data model change with ripple to repos, template, routes | Out of MVP. Revisit if sessions routinely get interrupted. |

---

## Feature Dependencies

```
Source ingestion (FILE / URL / TOPIC)
    └── User prompt
            └── LLM generation (structured: Note + Cards)
                    └── Draft store (in-memory)
                            └── Review UI (edit / reject / approve)
                                    └── Atomic save (Source + Note + Cards)
                                            └── Source detail (read notes, list cards)
                                            └── Drill (filter → deck → rate → log)
                                                    └── CardReview log
                                                            ├── Session summary
                                                            └── [Phase 3] SRS scheduling
                                                                    └── [Phase 3] "Due today" drill
                                                                    └── [Phase 3] Streaks / heatmap
                                            └── [Phase 4+] Search

URL fetcher ──required_by──> URL-kind generation
File reader ──required_by──> FILE-kind generation
LLM provider port ──required_by──> All generation + [Phase 2] mock-interview grading

[Phase 2] Retriever + EmbeddingProvider
    └── FOLDER-kind generation (RAG)
            ──shares_infra──> [Phase 4+] Semantic search

[Phase 2] Mock-interview mode
    └── requires: LLM provider (reused)
    └── requires: Typed-answer input UI (new)
    └── requires: "Grade" use case (new)
    └── independent_of: SRS, RAG

[Phase 3] SRS
    └── requires: CardReview log (present in MVP — critical that this lands day 1)
    └── changes: Drill entry point (filter → "due cards")
    └── optional_finer_grain: Rating enum expansion (binary → 4-grade)
```

### Dependency Notes

- **CardReview log is a hard Phase-1 dependency for Phase 3 SRS.** This
  is already in MVP. Key insight: even without SRS logic, *the log must
  be append-only and timestamped correctly from day one*, or Phase 3
  backfill is painful. Spec §3 has this right.

- **Review-before-persist depends on the draft store.** The in-memory
  draft store is a small, well-scoped component but it's on the critical
  path of every generation flow. If draft store is brittle (e.g. token
  collision, TTL bugs), the whole generation UX suffers. Treat as a
  first-class component, not an implementation detail.

- **LLM provider port is shared across Phase 1, Phase 2 mock-interview,
  and Phase 2 RAG.** Three consumers. Worth designing the port surface
  carefully in MVP even though only one method is used initially (spec
  §4.3 notes it'll grow).

- **RAG retrieval and semantic search share embedding infrastructure.**
  Phase 2 sets up the vector store; Phase 4+ search reuses it. No
  duplicate infra.

- **Tag model is unconstrained / free-form.** This is a feature, not a
  bug, but it means "filter by tag" and "autocomplete existing tags"
  (small UX nicety) depend on a lightweight tag-listing query. Trivial
  to add; flag it.

- **Mock-interview mode is independent of RAG and SRS.** Could ship in
  its own phase if RAG turns out to be a rabbit hole. Good modularity.

- **Regeneration overwrites notes, appends cards.** This is a subtle
  dependency on _user trust in the review step_. If review is too
  tedious, users will stop regenerating, which stalls the whole
  generate→drill loop. Watch UX here post-MVP.

---

## MVP Definition

### Launch With (v1) — matches Dojo's Phase 1

Dojo's scoped MVP (PROJECT.md Active + spec §1, §10) is a well-cut
MVP by the table-stakes-plus-one-differentiator rule. Listed here for
cross-reference:

- [x] Generate notes + Q&A cards from FILE / URL / TOPIC
- [x] User prompt shapes every generation
- [x] Review (edit / reject / approve) before any DB write
- [x] Atomic save (Source + Note + approved Cards)
- [x] Drill with Space / ← / → + on-screen buttons + slide-off animation
- [x] Filter drill by source or tag
- [x] Read notes rendered from markdown; link back to cards
- [x] Free-form tags, default-copied from source, per-card editable
- [x] Append-only CardReview log
- [x] Single LLM provider behind a port (Anthropic)
- [x] API key via env (never in DB/UI)
- [x] Test pyramid, fakes at DIP boundaries, >90% coverage, pristine output
- [x] `make check`, pre-commit, CI all green
- [x] Architecture docs (4 Mermaid diagrams) + repo-root `CLAUDE.md`

### Missing from MVP — gaps to confirm with Danny before roadmap

The questions below are **requirements-review gaps**, not re-proposals
of scope. Each is a table-stakes feature that could be in MVP implicitly
or not at all. Confirm each:

- [ ] **Gap #1: Post-save card editing / deletion.** PROJECT.md says users
  can edit/reject *during review*, but doesn't explicitly say they can
  edit a saved card's question/answer or delete a saved card. For any
  flashcard app, post-save editing is table stakes — users catch typos,
  fix wording, remove duplicates after drilling. Complexity LOW (one
  route + template). **Recommendation:** add as MVP requirement; it's ~2
  hours and closes a user-expectation hole.

- [ ] **Gap #2: Markdown rendering inside card question/answer in drill view.**
  Spec confirms notes render via `markdown-it-py` in the Read view.
  It's not explicit that the *drill UI* renders markdown on the
  back/front of a card. For an MLOps domain this matters — answers
  like "`kubectl get pods -n kube-system`" in a monospace code block
  read very differently from the same text as plain prose, and YAML
  snippets need a `<pre>` to stay legible. Complexity LOW (reuse the
  same renderer). **Recommendation:** explicit MVP requirement that
  card question and answer render as sanitized markdown in both the
  review UI and drill UI.

- [ ] **Gap #3: Drill session length cap / "study N cards" control.**
  Spec says filter by source or tag, and deck is drawn in random
  order. No mention of capping session length. If a user's source
  generates 40 cards and they filter to "k8s" (which covers 3 sources
  = ~100 cards), they might want to drill 20. Complexity LOW (a form
  field on the drill-start page, `LIMIT N` in the query).
  **Recommendation:** optional requirement; could also be Phase 2.
  Not a blocker but flag-worthy.

None of these three are architectural. All three are surface-UI
completeness items. Decide with Danny whether they're MVP or v1.1.

### Add After Validation (v1.x / Dojo Phase 2)

- [x] **FOLDER source kind + RAG** (spec §10 Phase 2) — unlocks "study
  from my whole wiki"
- [x] **Mock-interview typed-answer mode** (spec §10 Phase 2) — the
  signature interview-prep feature
- [ ] **PDF ingestion** — add if users actually want it; if not, skip
- [ ] **Bulk card actions in review** (select all / approve all / delete
  selected) — if decks routinely exceed ~30 generated cards per
  session, one-by-one review becomes fatiguing

### Future Consideration (v2+ / Dojo Phase 3+)

- [x] **SRS scheduling** (Phase 3)
- [x] **Streaks, heatmap, weak-cards indicator** (Phase 3)
- [x] **Second LLM provider** (Phase 4, validates port)
- [x] **Local LLM (Ollama)** (Phase 4)
- [x] **SQLite FTS5 search** (Phase 4+)
- [x] **Anki export** (Phase 4+)

### Explicitly Out of Scope (all confirmed — not to be revisited)

From Dojo's §11 + PROJECT.md, all remain correct and re-confirmed by
this research:

- Multi-user / auth
- Server deployment / cloud
- Card versioning
- Simultaneous multi-provider LLM in MVP
- Real-time updates / websockets
- Advanced observability
- Rich WYSIWYG editor
- Image / LaTeX / audio in cards
- Gamification (XP/levels/badges; streaks are Phase 3)
- AI-tutor chat mode
- Prompt-template editor in UI
- Auto-tagging
- Social features / sharing / leaderboards
- Import from competitors (MVP)
- Full `make db-reset` target

---

## Feature Prioritization Matrix

Rating the table-stakes + differentiator set against user value and
implementation cost. "Priority" assumes Dojo's Phase-1 MVP frame.

| Feature | User Value | Impl Cost | Priority | Notes |
|---|---|---|---|---|
| Generate from FILE | HIGH | MED | **P1** | Primary ingestion; Black Lodge docs are first-day content |
| Generate from URL | MED | MED | **P1** | Adds breadth (blog posts, docs); trafilatura does the heavy lifting |
| Generate from TOPIC alone | MED | LOW | **P1** | Cheapest kind to ship; big unlock for "I don't have a doc handy" |
| User prompt on every generation | HIGH | LOW | **P1** | Differentiator; tiny code cost |
| Review-before-save (edit/reject) | HIGH | MED | **P1** | Trust foundation; without this, whole pipeline loses credibility |
| Atomic save | HIGH | LOW | **P1** | Data integrity table stake |
| Drill (Space / ← / →) | HIGH | MED | **P1** | Core loop |
| Card slide-off animation | MED | LOW | **P1** | Differentiator *feel*; CSS-only; keep in |
| Filter drill by source | HIGH | LOW | **P1** | Required for usable library at >50 cards |
| Filter drill by tag | HIGH | LOW | **P1** | Same |
| Free-form tags | MED | LOW | **P1** | Enables filtering |
| Read view (markdown notes) | HIGH | LOW | **P1** | Reading mode ≠ drill mode; both needed |
| CardReview append-only log | HIGH | LOW | **P1** | Phase-3 prerequisite; cheap now |
| Session summary (X/Y, duration) | MED | LOW | **P1** | Table stake for drill UX |
| Shuffle deck | MED | LOW | **P1** | Table stake |
| LLM port (Anthropic concrete) | HIGH | MED | **P1** | Architecture foundation |
| API key via env | HIGH | LOW | **P1** | Security table stake |
| Markdown in card Q/A (drill UI) | HIGH | LOW | **P1*** | **Gap #2** — recommend adding explicitly |
| Post-save card edit/delete | HIGH | LOW | **P1*** | **Gap #1** — recommend adding explicitly |
| Drill-session size cap | MED | LOW | **P2** | **Gap #3** — MVP-or-v1.1 |
| FOLDER + RAG | HIGH | HIGH | **P2** | Phase 2; big win but complex |
| Mock-interview mode | HIGH | HIGH | **P2** | Phase 2; signature feature |
| SRS scheduling | HIGH | MED | **P3** | Phase 3 |
| Streaks / heatmap | MED | LOW-MED | **P3** | Phase 3; derivable from log |
| Second LLM provider | MED | LOW | **P3** | Phase 4; validates abstraction |
| Local LLM (Ollama) | MED | MED | **P3** | Phase 4 |
| FTS search | LOW-MED | MED | **P3** | Phase 4+ |
| Anki export | LOW | MED | **P3** | Phase 4+; users rarely leave |
| PDF ingestion | MED | MED-HIGH | **P3** | Phase 2+ if requested |
| YouTube transcript ingest | LOW | MED-HIGH | **P3** | Unclear fit for MLOps-interview-prep |

*P1 marked with asterisk = currently not explicit in Dojo MVP; recommend
explicit inclusion.*

---

## Competitor / Reference Feature Analysis

Comparison framed to show where Dojo sits. **LOW confidence** on
specific competitor feature details for 2026 (product lines shift); the
*categorical* positioning is **MEDIUM-HIGH** confidence.

| Feature | Anki | Quizlet | RemNote | Wisdolia / Quizgecko / StudySmarter | Dojo MVP |
|---|---|---|---|---|---|
| Card authoring | Hand-authored (or add-on) | Hand-authored (+ some AI) | Hand + AI from notes | AI-generated from upload | **AI from file/URL/topic + user prompt** |
| Review before save | Implicit (edit before save is manual) | N/A (hand-authored) | Yes (notes are canonical) | No — AI dumps into library | **Yes, explicit, atomic** |
| SRS | Yes (SM-2 / FSRS) | Limited ("Learn" mode) | Yes (built-in) | Variable; often none | **Phase 3** |
| Local-first | Yes (desktop Anki) | No (SaaS) | Partial (desktop app, cloud sync) | No (SaaS, cloud) | **Yes, localhost-only** |
| Provider-swap LLM | N/A (plugins) | No | No (built-in) | No | **Yes, port-based** |
| Markdown / code cards | Via add-ons | Weak | Good (notes-first) | Variable | **Yes (planned via `markdown-it-py`)** |
| Drill interaction | Keyboard + rating | Multiple modes, click-heavy | Keyboard | Click-heavy | **Keyboard-first, arrow+Space+slide** |
| Mock-interview typed answers | No | No | No | Some adjacent products | **Phase 2** |
| RAG over your own notes | No | No | Partial (note-linked) | Some do | **Phase 2** |
| Privacy (no data sent out) | Yes | No | No | No | **Yes (modulo LLM API call with source text)** |
| Cost | Free | Freemium | Freemium | Subscription | **Free + your API spend** |

**Positioning read:** Dojo is closest to _Anki + an AI card-generator
plugin, but local-first and with a reviewer step the plugins don't
do well_. The competitive story is:

1. **Anki's retention story** (SRS, local) — matches Phase 3 onward.
2. **AI-study app's generation story** — matches MVP.
3. **Neither competitor does both well in one place** — that's the gap.

The mock-interview mode in Phase 2 is the feature that separates Dojo
from _both_ camps.

---

## Gaps to Flag for Requirements Review (summary)

Three MVP table-stakes gaps already detailed above. Listed here as a
clean action list for Danny:

1. **Gap #1 — Post-save card edit / delete.** Almost certainly intended
   but not explicit in PROJECT.md. Confirm as MVP or v1.1.
2. **Gap #2 — Markdown rendering in card Q/A during drill.** Critical
   for MLOps-domain code in cards. Confirm as explicit MVP requirement.
3. **Gap #3 — Drill session size cap.** Optional-feel, low cost;
   confirm MVP or Phase 2.

Additionally, two non-gap observations worth logging:

4. **Observation — Rating is binary in MVP.** Fine for pre-SRS, but
   Phase 3 SRS will likely want Again/Hard/Good/Easy (SM-2) or a
   confidence slider (FSRS). Expanding the `Rating` enum later is a
   migration; flag as a Phase-3 entry-cost, not an MVP change.

5. **Observation — Draft-loss-on-restart is a deliberate tradeoff.**
   Acceptable for single-user local. Worth surfacing in the UI
   ("drafts expire in 30 min") to set user expectation. Copy-only,
   not architecture.

---

## Sources

Ecosystem sampling drawn from training-data knowledge of:

- **Classic flashcard apps:** Anki (anki.net), Mnemosyne, SuperMemo,
  Quizlet, Brainscape, Mochi (mochi.cards), Orbit (andymatuschak.org).
- **Notes-first tools with SRS:** RemNote, Obsidian +
  obsidian-spaced-repetition plugin, Logseq flashcards.
- **LLM-powered generators (2023-2025 wave):** Wisdolia, Quizgecko,
  StudySmarter, Monic.ai, ChatGPT-via-Custom-GPT workflows,
  Notion-AI-flashcard setups, Studdy Buddy.
- **Interview-prep adjacent:** LeetCode spaced-review add-ons,
  Pramp / Interviewing.io (different product shape but informs
  mock-interview expectations).
- **Research:** Piotr Wozniak's SuperMemo papers (SM-2, SM-17),
  FSRS algorithm (Ye, 2023). These inform the SRS-in-Phase-3 note.

**All category-level claims** (what SRS is, what review-before-save
does, what markdown-in-cards requires) are HIGH confidence because
these patterns are stable and widely documented.

**Product-specific feature claims** (e.g., "RemNote does X in 2026")
are LOW confidence — the LLM-study-app space has been moving fast.
Before Dojo makes a product decision that hinges on "competitor X
already does / doesn't do Y," re-verify with current sources.

---

*Feature research for: Dojo — local LLM-powered MLOps interview-prep study app*
*Researched: 2026-04-18*
