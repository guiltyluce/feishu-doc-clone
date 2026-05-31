# Browser Image Extraction

Use this reference when `docs +media-download` or `docs +create` cannot read source image tokens, but the logged-in browser can display the source document.

## Playwright Flow

1. Open the source document in a logged-in browser:
   ```js
   await page.goto("https://.../wiki/...");
   ```

2. Scroll the Feishu document container so lazy images load:
   ```js
   await page.evaluate(async () => {
     const scroller = document.querySelector(".bear-web-x-container") || document.scrollingElement;
     const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
     for (let y = 0; y <= scroller.scrollHeight - scroller.clientHeight + 400; y += 450) {
       scroller.scrollTop = y;
       await wait(800);
     }
   });
   ```

3. Fetch images with page credentials and save base64 JSON. Pass the image token list from `clone_plan.json`; in MCP Playwright use `browser_evaluate` with `filename: "feishu_images_base64.json"`. MCP `browser_evaluate` does not pass external arguments, so paste `const tokens = [...]` inside the function body before running the snippet.

   ```js
   async (tokens) => {
     const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
     const scroller = document.querySelector(".bear-web-x-container") || document.scrollingElement;
     const seenSrc = new Map();

     for (let y = 0; y <= scroller.scrollHeight - scroller.clientHeight + 400; y += 450) {
       scroller.scrollTop = y;
       await wait(800);
       for (const img of document.querySelectorAll("img.docx-image")) {
         const src = img.currentSrc || img.src || "";
         for (const token of tokens) {
           if (src.includes(token) && !seenSrc.has(token)) seenSrc.set(token, src);
         }
       }
     }

     const toBase64 = (buffer) => {
       let binary = "";
       const bytes = new Uint8Array(buffer);
       for (let i = 0; i < bytes.length; i += 0x8000) {
         binary += String.fromCharCode(...bytes.subarray(i, i + 0x8000));
       }
       return btoa(binary);
     };

     const urlFallbacks = (token) => [
       seenSrc.get(token),
       `https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/preview/${token}/?preview_type=16`,
       `https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/v2/cover/${token}/?fallback_source=1&height=1280&mount_point=docx_image&policy=equal&width=1280`,
       `https://internal-api-drive-stream.feishu.cn/space/api/box/stream/download/${token}/`,
     ].filter(Boolean);

     const results = [];
     for (const token of tokens) {
       let record = { token, ok: false, attempts: [] };
       for (const url of urlFallbacks(token)) {
         try {
           const res = await fetch(url, { credentials: "include" });
           const type = res.headers.get("content-type") || "";
           const buffer = await res.arrayBuffer();
           record.attempts.push({ status: res.status, type, size: buffer.byteLength });
           if (res.ok && type.startsWith("image/") && buffer.byteLength > 1000) {
             record = { token, ok: true, type, size: buffer.byteLength, base64: toBase64(buffer) };
             break;
           }
         } catch (error) {
           record.attempts.push({ error: String(error) });
         }
       }
       results.push(record);
     }
     return results;
   }
   ```

4. Decode to files:
   ```bash
   mkdir -p /tmp/feishu-doc-assets
   jq -r '.[] | select(.ok) | [.token, (.type|split("/")[1]), .base64] | @tsv' feishu_images_base64.json |
   while IFS=$'\t' read -r token ext b64; do
     [ "$ext" = "jpeg" ] && ext=jpg
     printf '%s' "$b64" | base64 -d > "/tmp/feishu-doc-assets/${token}.${ext}"
   done
   ```

If browser extraction returns fewer images than the plan, scroll directly near each missing image block and inspect `img.docx-image` elements again. Feishu lazy-renders aggressively.
