---
name: pls
description: Publish a document, report, page or HTML file as a NOISE-styled web page at https://pls.n0.beer and return a shareable link that expires (24 hours by default, up to 7 days). Use when the user wants to share, publish, serve or host something, asks for "a link", "a URL" or "a tunnel URL", says "share this" or "put this on pls", mentions pls.n0.beer, or wants an HTML page other people can open. Also lists and deletes published pages. Never use third-party tunnels or other hosts to share pages.
---

# pls: publish pages to pls.n0.beer

`pls.n0.beer` is NOISE's self-hosted page-sharing service. This skill turns a document into a page in the NOISE design (sage ground, the wordmark masthead, mono data) and publishes it. Anyone with the link can view the page until it expires.

The tool is one script, run with `uv` (its dependencies install themselves):

```
uv run ~/.agents/skills/pls/scripts/pls.py <command> ...
```

| Command | What it does |
|---|---|
| `publish <file> [--ttl 24h] [--title T] [--page-name P] [--raw] [--wrap] [--inline]` | Build the page, upload it, print the URL, expiry and size |
| `render <file> [same options] [-o out.html]` | Build the final HTML locally without publishing (footer reads "Preview, not published.") |
| `list` | Show your published pages: ref, title, created, expires, size |
| `delete <url-or-id>` | Delete a page now |

`--ttl` takes `90m`, `24h`, `3d`, `7d` (60 seconds to 7 days, default 24h). `--page-name` is the label beside the wordmark (default "Shared page"). Both default sensibly, so most publishes are just `publish <file>`.

## Which design to use

Default to the NOISE design. Build the page from `~/.agents/skills/pls/template.html` and the class vocabulary below. Do not invent classes, add `<style>` blocks, or bring your own design system; the server's stylesheet (`https://pls.n0.beer/_/pls.css`) styles exactly this vocabulary.

A NOISE page links the shared stylesheet and fonts from `/_/` on the same host, so browsers cache them and each page carries only its own HTML (a few KiB). Pass `--inline` only when the user wants one self-contained file (for example to keep or send offline): the script then embeds the server's current `pls.css` and both fonts (about 216 KiB) as a snapshot of the design.

Publish a page in some other design only when the user asks for one. Then write a full HTML document and publish it with `publish file.html` (a document containing `<html` or `<!doctype` goes up as-is) or `--raw` (bytes untouched).

## Input handling

| You have | Do this |
|---|---|
| Markdown or text (`.md`, `.markdown`, `.txt`) | `pls.py publish file.md`. Rendered into the NOISE shell; `.txt` is treated as Markdown. |
| An HTML fragment (no `<html`/`<!doctype`) | `pls.py publish body.html`. Wrapped in the NOISE shell automatically. |
| A full HTML document | `pls.py publish page.html` publishes it as-is. Add `--wrap` only for a bare document that should get the NOISE shell (its body is kept, its `<style>` and `<script>` are dropped). |
| PDF, DOCX, notes, chat content, data, anything else | Write Markdown or an HTML body first using the vocabulary below, save it under `~/.t3/artifacts/<slug>/` (or a temp dir), then publish that file. |

Before publishing something you converted, make sure it says what the source says: do not summarize or reword unless asked.

## The NOISE vocabulary

The shell supplies `body > .wrap`, `header.masthead` (wordmark, page name, date stamp), `main.doc` and `footer.foot`. You write what goes inside `main.doc`, or Markdown that becomes it.

Plain elements need no classes: one `h1`, then `h2`, `h3`, `h4`, `p`, `ul`/`ol`, `blockquote`, `pre > code`, `code`, `a`, `hr`, `img`, `svg`, `figure`/`figcaption`, `details`/`summary`, `strong`. Step headings one level at a time.

Extra pieces, and only these:

- `p.lede`: the one-sentence summary under the h1.
- Tables: wrap in `<div class="scroll">` (the script does this for you). `thead th`, `tbody tr`, `th[scope=row]` for the row label, `tfoot` for totals. Numbers go in `td.num` or `th.num` (mono, right-aligned); a Markdown column marked `---:` is converted to the same thing. `.sub` is a secondary mono line under a cell's main text: `<th scope="row">Referral<div class="sub">3 campaigns</div></th>`.
- `dl.kv`: label and value rows (`dt`/`dd` pairs).
- `dl.tiles > div.tile > dt + dd`: stat tiles for headline numbers; `dd` may end with `<small>` for context: `<dd>4,812<small>+12% on last week</small></dd>`.
- `ul.notes`: a ruled list of findings. Lead each item with a `<strong>` sentence.
- `span.bar > i`: an inline single-series bar, `<span class="bar"><i style="width:41%"></i></span>`. Put the number beside it; the bar is not the only carrier of the value.
- `.mute`: secondary text.

Data reports use tiles for the three to six headline numbers, then tables with `td.num`, bars for share-of-total columns, and `ul.notes` for findings. `~/.agents/skills/pls/examples/report-body.html` shows every piece; copy its structure.

Style rules, from the NOISE design guide:

- One `h1`, which is the page title. The script adds one from the title if the body has none; do not write a second.
- Rules carry the structure. No boxes, cards, shadows, gradients, colored badges or banners.
- Do not let color carry meaning, and never use red or green. Market moves and changes are signed numbers (`+12%`, `-6%`).
- Copy: sentence case, plain words, short sentences. No ALL-CAPS labels. In headings, labels and captions you write, join facts with commas and periods rather than middle dots, em dashes, arrows or pipes. Counts are literal with separators (`4,812`). Durations are `45s`, `3h 12m`, `2d 4h`. Clock times are 24-hour. Leave the user's own quoted text alone.
- No emoji as icons. For an inline SVG chart, use `currentColor` so it follows the theme.
- Pages are single files. Embed images as data URIs or inline SVG rather than linking local paths. The limit is 16 MiB.

Markdown specifics (extensions: tables, fenced code, sane lists, heading ids, attribute lists):

```markdown
# Weekly signup report

Signups rose 12% on the week, led by referrals.
{: .lede }

| Channel     | Signups | Change |
| ----------- | ------: | -----: |
| Referral    |   1,984 |   +22% |
| Paid search |     901 |    -6% |
```

Indent nested list items by four spaces (two spaces does not nest). For the tile, bar and notes pieces inside Markdown, write them as raw HTML blocks with no blank lines inside the block and a blank line before and after. For a report that is mostly those pieces, write an HTML body instead.

## Optional: check it before publishing

For anything with tables, tiles or charts, render locally and look at it:

```
uv run ~/.agents/skills/pls/scripts/pls.py render report.md -o /tmp/pls-preview.html
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" --headless=new --hide-scrollbars \
  --window-size=1200,2400 --screenshot=/tmp/pls-preview.png file:///tmp/pls-preview.html
```

On Linux, use `google-chrome` instead of the `/Applications/...` browser path. A sandboxed Chrome headless build on `PATH` supports the same screenshot flags.

Then open `/tmp/pls-preview.png` with the Read tool. The preview loads the stylesheet and fonts from pls.n0.beer, so it needs a connection; add `--virtual-time-budget=5000` to the Chrome command or the fonts may not have loaded when the screenshot is taken. Delete the temp files afterwards.

## After publishing

`publish` prints the URL, the expiry in the user's local time and the size. Reply with:

1. The URL.
2. When it expires, in local time (for example "Mon 6 Oct 2026, 1:05 PM EDT").
3. One line that anyone with the link can view it until then.

Offer `pls.py list` and `pls.py delete <url-or-id>` only if relevant (for example when the user wants it gone sooner). Pass `--ttl` when the user wants a different lifetime ("keep it for a week" is `--ttl 7d`).

## Rules

- Never share pages through third-party tunnels or hosts (localhost.run, ngrok, cloudflared quick tunnels, pastebins, file-sharing sites). pls.n0.beer is the only place pages go.
- Never put credentials, tokens, API keys, logs, database contents, exported runtime data or other sensitive material in a published page. If the content might include any, stop and ask the user first. The page is readable by anyone who has the link.
- Never print the publish token.

## Configuration and failures

- Token: the `NOISE_PLS_TOKEN` environment variable, else the macOS Keychain item `noise-pls-publish` (account `default`), then the NOISE repo's root `secrets.edn` under `:pls-site :publish-token`. The script checks `~/Github/noise`, `~/github/noise`, and `~/GitHub/noise`; set `NOISE_PLS_SECRETS_FILE` to the real file (on Goat's Mac `~/.config/noise/secrets.edn`, which the checkout's root `secrets.edn` symlinks to) when the repo lives elsewhere or has no root file. This works on Linux without a Keychain or a persistent token environment variable. Keep the token in that canonical file; do not copy it anywhere else. On macOS, `security add-generic-password -a default -s noise-pls-publish -w` also adds it to the Keychain and prompts for the value.
- Server: `https://pls.n0.beer`, overridable with `NOISE_PLS_BASE`.
- A connection error means the service may not be deployed yet or the machine is offline; tell the user rather than retrying with another host.
- API errors print the server's message and code with a non-zero exit (a bad TTL, a page over 16 MiB, an unknown id on delete).
