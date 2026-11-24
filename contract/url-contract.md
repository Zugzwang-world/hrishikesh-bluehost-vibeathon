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
| host | Origin where Add look to bag goes. Missing: use `DEFAULT_HOST` from web/src config. Neither: show the bag summary in place. |
| try | One SKU to equip on load. |
| look | Comma-separated SKUs to equip on load (applied before try). |
| event | Preselects the occasion chip. `keynote` = On stage, Bluehost Bangalore. |

## Add look to bag

A normal link with `target="_top"`:

```
HOST/cart?add=SKU,SKU,SKU&look=LOOK_TITLE
```

- `add` is the comma-separated SKUs of the equipped look (required slots first, in slot order).
- `look` is the look title, URL-encoded (encodeURIComponent).
- Bonus: also `window.parent.postMessage({ type: "ensemble:add-look", skus, look }, "*")`.

## Bluehost side (built from the Part 2 prompts; reference only)

- `/cart` reads `add` and puts those SKUs in the bag.
- `/stage` embeds the Stage with `embed=1&host=<its own origin>`.
- Product pages link to `/stage?try=SKU`, passed through to the iframe.

## Stable asset URLs (never rename)

Placeholders first, real renders later under the same names. No broken images, ever.

- /catalog/catalog.json, /catalog/merchants.csv, /catalog/products.csv
- /products/SKU.webp (800 x 1000)
- /merchants/SLUG.png (wordmark, transparent) and /merchants/SLUG-banner.jpg (1600 x 600)
- /brand/hero.jpg (1920 x 1080), /brand/persona.png (1200 x 1500, transparent), /brand/logo.png
- /models/avatar.glb, /models/wardrobe.glb, /models/stage.glb
- /textures/PATTERN.png (stripe, check, denim, melange, corduroy; prints as /textures/print-SLUG.png)

CORS: `Access-Control-Allow-Origin: *` on /catalog, /products, /merchants, /brand, /models, /textures. Framing: `Content-Security-Policy: frame-ancestors *`.
