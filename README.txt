OFSS AI Studio — Text-to-Speech starter
======================================

What this is
------------
A static, responsive Text-to-Speech demo. It uses the visitor's built-in browser/device speech synthesis voices. No API key or backend is required for playback.

Important limitation
--------------------
This version plays speech in the browser. It does NOT generate an MP3/WAV download. For downloadable files and consistent AI voices, you will need a separate TTS backend/model or third-party service; free usage is typically limited and not guaranteed.

Deploy with Cloudflare Pages
----------------------------
1. Extract this ZIP. Keep index.html at the root of the project.
2. Create a GitHub account and a new PUBLIC repository (for example: ofss-ai-studio).
3. In the repository choose Add file > Upload files; upload index.html and README.txt; commit.
4. Create a Cloudflare account at https://dash.cloudflare.com/
5. Open Workers & Pages > Create > Pages > Connect to Git.
6. Select your repository.
7. Framework preset: None. Build command: leave empty or use `exit 0` if required. Build output directory: `/` or the repository root as accepted by the current dashboard.
8. Deploy. Test the assigned `*.pages.dev` URL first.

Connect ai.ofssbiharboard.com
-----------------------------
1. In your Pages project, open Custom domains > Set up a custom domain.
2. Enter ai.ofssbiharboard.com and follow the verification steps.
3. If Cloudflare shows a CNAME target, open GoDaddy > Domain Portfolio > ofssbiharboard.com > DNS.
4. Add a CNAME record:
   Type: CNAME
   Name/Host: ai
   Value/Points to: YOUR-PROJECT.pages.dev (use the exact hostname shown by Cloudflare)
   TTL: Default
5. Do NOT change nameservers or existing records for the root domain unless you understand the effect. Do not delete MX records.
6. Wait for DNS/SSL activation, then test https://ai.ofssbiharboard.com

Notes
-----
- Dashboard labels may change slightly over time.
- A public GitHub repository exposes the source code. Never put passwords, private tokens, or API keys in index.html.
- Browser voices vary by device and browser. Test in an updated Chrome or Edge browser.
