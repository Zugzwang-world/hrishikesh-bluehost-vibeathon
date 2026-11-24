# URL contract

Stage = this repo on Vercel (https://hrishikesh-stage.vercel.app until a final URL is logged in DECISIONS.md).
Bluehost = the entry built in Bluehost AI Builder (HOST below is its origin, for example https://NAME.app.bluehost.ai).

## Stage address

```
https://STAGE/?embed=1&host=HOST&try=SKU&look=SKU,SKU&event=keynote
```

| Param | Meaning |
| --- | --- |
| embed | `1` hides the Stage's own header chrome for the Bluehost iframe. |
| mode | `persona`: avatar on the stage in the default look, slow orbit, no UI. `locked` (with `look`): turntable of that look, no UI. |
| cartPath | Overrides CART_PATH (default `/cart`), e.g. for hash routing. |
| host | Origin where Lock the look goes. Missing: use `DEFAULT_HOST` from web/src config. Neither: show the bag summary in place. |
| try | One SKU to equip on load. |
| look | Comma-separated SKUs to equip on load (applied before try). |
| event | Preselects the occasion chip. `keynote` = On stage, Bluehost Bangalore. |

## Lock the look (was Add look to bag)

A normal link with `target="_parent"` (the Bluehost editor preview is itself an iframe):

```
HOST + CART_PATH + ?add=SKU,SKU,SKU&look=LOOK_TITLE
```

- `add` is the comma-separated SKUs of the equipped look (required slots first, in slot order).
- `look` is the look title, URL-encoded (encodeURIComponent).
- Bonus: also `window.parent.postMessage({ type: "ensemble:add-look", skus, look }, "*")`.

## Product viewer

`https://STAGE/product?sku=SKU&embed=1`: the single piece on an invisible mannequin, slow turntable (storefront drawers).

## Bluehost side (built from the Part 2 prompts; reference only)

- `/cart` reads `add` and `look`, puts those SKUs in the bag and embeds `STAGE/?embed=1&mode=locked&look=SKUs`.
- `/experience` embeds the Stage with `embed=1&host=<its own origin>`, passing `try` and `look` through.
- `/p/hrishikesh` embeds `STAGE/?embed=1&mode=persona`.
- Storefront drawers (`/m/SLUG`) embed `STAGE/product?sku=SKU&embed=1` and link to `/experience?try=SKU`.

## Stable asset URLs (never rename)

Placeholders first, real renders later under the same names. No broken images, ever.

- /catalog/catalog.json, /catalog/merchants.csv, /catalog/products.csv
- /products/SKU.webp (800 x 1000)
- /merchants/SLUG.png (wordmark, transparent) and /merchants/SLUG-banner.jpg (1600 x 600)
- /brand/hero.jpg (1920 x 1080), /brand/persona.png (1200 x 1500, transparent), /brand/logo.png (SHOP-UNI-FY)
- /portfolio/01.webp to /portfolio/04.webp (public portfolio photos)
- /models/avatar.glb, /models/wardrobe.glb, /models/stage.glb
- /textures/PATTERN.png (stripe, check, denim, melange, corduroy; prints as /textures/print-SLUG.png)

CORS: `Access-Control-Allow-Origin: *` on /catalog, /products, /merchants, /brand, /models, /textures, /portfolio. Framing: `Content-Security-Policy: frame-ancestors *`.
