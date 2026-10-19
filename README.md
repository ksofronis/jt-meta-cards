# JT Home Design: Meta catalog product cards

Handover document for the developer maintaining the JT Home Design website and product feed.

## 1. Purpose

Meta catalog ads (Advantage+ catalog / DPA) render product images inside square cards. In Instagram and Facebook Stories they appear as a grid. The website's product photos are mostly landscape (3:2), so each card showed a small photo with large white bands above and below, and no product information.

This project replaces each product's main catalog image **in Meta only** with a square card (1080×1080) that keeps the original photo uncropped and uses the bands for:

- the product name (top band),
- a USP badge, only when the product description states that feature,
- dimensions taken from the product title, when present,
- the store phone number with the phone icon used in the newsletters.

No price is shown on the card, because a static image cannot follow price changes.

Nothing changes on the website, in WooCommerce, or in the wpwoof feed (`facebook.xml`). Product data (titles, prices, stock, links, exclusions) keeps coming exclusively from the existing feed.

## 2. How it works

```
jthomedesign.gr (WooCommerce + wpwoof)
   └─ facebook.xml ──────────────► Meta primary feed "NO ORION FEED" (unchanged, REPLACE every 3h)
                                        ▲
GitHub repo ksofronis/jt-meta-cards     │ supplementary feed overrides image_link only
   ├─ item/<g:id>.jpg  (cards)          │
   ├─ manifest_items.json               │
   └─ feed/supplementary.csv ───────────┘ Meta supplementary feed (hourly, :06)
        ▲
   GitHub Action "meta-feed" (hourly, :35) rebuilds supplementary.csv
```

1. Cards are generated once per product and published on GitHub Pages at `https://ksofronis.github.io/jt-meta-cards/item/<g:id>.jpg`.
2. `manifest_items.json` records, for every card, the original `image_link` and `title` it was built from.
3. Every hour a GitHub Action downloads the live wpwoof feed and writes `feed/supplementary.csv` with two columns, `id` and `image_link`. A product is included only when its current photo **and** title in the live feed still match the manifest. Otherwise it is left out and Meta keeps the original photo.
4. A Meta **supplementary feed** reads that CSV hourly and overrides `image_link` for the listed products. A supplementary feed cannot add or delete products; it only updates fields of products that already exist in the primary feed.

## 3. Repository contents

| Path | Role |
|---|---|
| `item/<g:id>.jpg` | One card per product (1,884 at build time). This is what Meta uses. |
| `manifest_items.json` | `{ "<g:id>": { "image": "<original image_link>", "title": "<original title>" } }` |
| `supp_order.txt` | Rollout order of product IDs. |
| `supp_count.txt` | How many IDs from `supp_order.txt` are currently included. The Action raises it by 300 per run until it covers all products. |
| `supp_build.py` | Builds `feed/supplementary.csv` from the live feed, manifest and count. |
| `feed/supplementary.csv` | File read by the Meta supplementary feed. |
| `.github/workflows/feed.yml` | Hourly job (minute 35): runs `feed_rewrite.py`, increments `supp_count.txt`, runs `supp_build.py`, commits changes. |
| `feed_rewrite.py`, `feed/facebook.xml` | Full copy of the wpwoof feed with card image links. Built hourly but **not used by Meta**. Kept as a fallback option only. |
| `generator/make_cards.py` | Card renderer (single source of the design and badge rules). |
| `generator/build_per_item.py` | Builds a card for every product in a feed file and writes `manifest_items.json`. |
| `generator/icon-phone-hi.png` | Phone icon (Tabler "phone" outline, same as the newsletters), colour #7A6645. |
| `cards/`, `u/` | Removed 19/10/2026 (pilot builds, never referenced by either feed; 243 MB freed for v9 under the 1 GB Pages limit). Still in git history. |
| `docs/` | Before/after illustration. |

## 4. Card design

- Canvas 1080×1080, white background.
- Top band 170 px: product name, Arial Bold, starting at 64 px and shrinking to fit (minimum 40 px). When the name is too long and contains " με ", the text after " με " is dropped (e.g. "Σαλόνι γωνία - κρεβάτι Nisos με αποθηκευτικό χώρο" becomes "Σαλόνι γωνία - κρεβάτι Nisos").
- Middle area: the original photo, never cropped, scaled to fit 1040×740 and centred. White borders already present in packshots are trimmed first. Transparent PNGs are flattened on white.
- Bottom band 170 px:
  - dimensions line (Arial, 44 px, colour #6E6458) when the title contains dimensions, e.g. `260x85x200` becomes `260×85×200 εκ.`; several sets are joined with commas;
  - phone line: icon plus `210 247 6585` (Arial Bold, 42 px, #222222).
- Badge: rounded pill at the top-left of the photo area, fill #6E6458, white Arial Bold 38 px.
- Output JPEG, quality 88.

The dimensions are removed from the name shown in the top band and shown only in the bottom band.

## 5. Badge rules

Badges are assigned from the feed's own text (title + description + product_type, lower-cased). The first matching rule wins; no match means no badge. Rules are deliberately strict so that the badge never claims something the description does not state.

| Badge | Matches (regex) |
|---|---|
| Γίνεται κρεβάτι | `μετατρέπεται σε κρεβάτι`, `γίνεται κρεβάτι`, `γωνία - κρεβάτι`, category `καναπέδες κρεβάτια` |
| Με αποθηκευτικό χώρο | `με αποθηκευτικό χώρο` |
| Ανοιγόμενο | title contains `τραπέζι` and description contains `ανοιγόμεν`, `επεκτειν` or `επιπλέον χώρο όποτε` |
| Στα μέτρα σας | `αλλαγής των (εργοστασιακών) διαστάσ`, `υφάσματος και διαστάσεων`, `στις διαστάσεις που επιθυμείτε` |
| Αδιάβροχο ύφασμα | `αδιάβροχ` followed within 25 characters by `ύφασμ` |
| Ελληνική κατασκευή | `ελληνικής κατασκευής` |
| Ξύλο δρυς | `από ξύλο δρυς`, `σε συνδυασμό με ξύλο δρυς`, `κατασκευ... από ξύλο δρυς` (wording about oak as a colour option does not qualify) |
| Best Seller | product_type contains `best sellers` |

## 6. Regenerating or adding cards

Requirements: Python 3 with Pillow. The renderer currently points to macOS Arial font paths (`/System/Library/Fonts/Supplemental/Arial*.ttf`). To run on Linux, change `FB` and `F` in `make_cards.py` to an available font with Greek support (e.g. Noto Sans); the look will differ slightly.

```bash
curl -sL -o feed.xml https://jthomedesign.gr/wp-content/uploads/wpwoof-feed/xml/facebook.xml
cd generator
FEED=../feed.xml python3 build_per_item.py      # writes cards_item/<id>.jpg and manifest_items.json
```

`build_per_item.py` skips cards that already exist. To rebuild a product (for example after a new photo or a renamed title), delete its file first. Then copy the new cards to `item/`, copy `manifest_items.json` to the repo root, and push. The next hourly run includes those products.

New products are **not** generated automatically. Until a card and manifest entry exist for them, they keep their original photo in Meta.

## 7. Safety design

- **Supplementary, not replacement.** The primary feed stays the source of every product. The supplementary file only overrides `image_link` and cannot create or delete products.
- **Match check.** A card is used only while the live photo and title equal those recorded in the manifest. Any change on the website automatically returns that product to its original photo.
- **Gradual rollout.** 300 more products per hour. A product whose image changes is temporarily `not_eligible` in Meta until Meta downloads the new image (observed: up to about 6 hours), so batching limits how much of the catalog is waiting at any moment.
- **Hosting.** Cards are served by GitHub Pages. If the repository is deleted or Pages stops serving, Meta cannot download the images and the affected products become ineligible. The repository must stay public and active.

## 8. Rollback

Any one of these returns all products to their original photos at the next Meta fetch:

1. Set `supp_count.txt` to `0` and push. The next run writes an empty supplementary file. Also disable the workflow, or it will increase the count again.
2. Delete the supplementary feed in Commerce Manager (Catalog → Data sources).

## 9. Meta configuration reference

| Item | ID / value |
|---|---|
| Catalog | `274689966805371` (JT Home Design - Official) |
| Primary feed | `1515676969568146` "NO ORION FEED", wpwoof URL, REPLACE every 3 hours |
| Supplementary feed | `993400956467226`, URL `https://ksofronis.github.io/jt-meta-cards/feed/supplementary.csv`, hourly |
| Feed rule: image pilot | `1612174003251775`, value_mapping on `image_link`, 20 pilot products. Can be deleted once the supplementary feed covers them. |
| Feed rule: brand | `1612189143250261`, fallback rule, `brand = "JT Home Design"` when empty. Fixes Meta's "missing brand/GTIN/MPN" error. Keep. |

## 10. Known limitations

- Meta's source prioritisation blocks the supplementary image for some products (warning "Some information in this feed couldn't be applied"; seen on 6 of 20 in the test). Those products keep their original photo.
- Some products share one photo with a different product on the website (e.g. "Καθρέπτης Napoli" uses the bedroom set photo). Each card shows the correct product name, but the photo is the one the website uses.
- Value-mapping feed rules are limited by Meta to about 20 entries, and regex feed rules sent through the API were not applied. That is why the supplementary feed is used.
- Pre-existing catalog diagnostics not related to images: 13 product IDs conflicting with group IDs, 2 products with empty price, products hidden from Shops. These come from the website data.

## 11. Automatic cards for new and changed products (added 10/10/2026)

Every hourly run of `meta-feed` now also runs `auto_cards.py` before `supp_build.py`:

- A product gets a new card when it is not in `manifest_items.json` (new product) or when its live photo or title differs from the one its card was built from (changed product). Maximum 60 per run.
- Cards use the same renderer and rules (`generator/make_cards.py`). On GitHub's Linux runner the font is Liberation Sans, which has the same letter widths as Arial; the visual difference is negligible.
- Each card is saved as `auto/<g:id>-<hash>.jpg` (the hash changes when the photo or title changes, so Meta downloads the new version) and recorded in `auto_manifest.json`.
- `supp_build.py` uses the automatic card only while it matches the live feed, so a later change on the website again falls back to the original photo until the next run makes a new card.
- A product that receives its first card, or a new one, is temporarily not eligible for catalog ads until Meta downloads the image (typically a few hours).
- The workflow now re-triggers itself permanently (about every 56 minutes), because GitHub's scheduled trigger is unreliable on this repository.

## 12. v9: instalments pill, cream backdrop, cards 2/3 and videos (added 19/10/2026)

- **Switch:** `v9.txt` = `on`. Rollback: empty the file. `v7_cards.py` then rebuilds every card back to v7/v8 (60 per run) and `supp_build.py` stops sending extras.
- **Card 1 (all products, `v7/`):** instalment pill on the photo, same split as the site: up to EUR 1,000 `Klarna · 3 άτοκες δόσεις`, up to EUR 10,000 `TBI · Έως 60 δόσεις`, none above. No monthly amount. White-background shots sit on a cream panel. The pill label is part of the file hash, so a card rebuilds when a price crosses EUR 1,000.
- **Extras (top products only, `v9x/`, `v9_extras.py`, `generator/make_v9x.py`):** `v9_top.txt` lists 200 ids (top by catalog-ad impressions, last 28 days to 19/10, plus Meta's top-48 by product views). Per product: card 2 colour range (only with swatches), card 3 dimensions + `Αχαρνές · Πανελλαδικά` + phone, video 9:16 and 1:1 (6 s, 60 fps, H.264 CRF 26). About 1.2 MB per product.
- **Feed:** `supplementary.csv` gains `additional_image_link` (cards 2/3 first, then the product's own site gallery, max 20; every row repeats its site gallery so nothing is blanked), `video[0].url` (9:16) and `video[1].url` (1:1). Extras are sent only while `v9x_manifest.json` matches the live photo, title, crop and price band.
- **Size budget:** GitHub Pages publishes at most 1 GB. Site after v9 is about 0.9 GB. Products dropped from `v9_top.txt` have their extras deleted on the next run. Do not grow the top list without checking the site size.
- **CI cost:** max 3 products' extras per hourly run (`V9X_MAX`); the step is non-blocking.
