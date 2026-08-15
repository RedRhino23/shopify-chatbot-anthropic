# shopify-chatbot-anthropic

A minimal Shopify App that injects a chatbot widget into storefronts via App Proxy and forwards messages to Anthropic's Messages API. This repository is a starter/demo. DO NOT store secrets in this repo.

Quick start
1. Create the app in Shopify Partners and set App URL and Redirect URL to your HOST (https://your-service.onrender.com).
2. Deploy to Render (or another host) and set environment variables (see .env.example).
3. Install the app on your test store using the OAuth install URL.
4. Add the widget to a store theme:
   <script src="https://{shop}.myshopify.com/apps/chatbot/widget.js"></script>

Environment variables (set these in Render or your host)
- ANTHROPIC_API_KEY
- ANTHROPIC_MODEL (default: claude-haiku-4-5)
- ANTHROPIC_VERSION (default: 2023-06-01)
- SHOPIFY_API_KEY
- SHOPIFY_API_SECRET
- HOST (your deployed URL)
- SHOPIFY_SCOPES (read_products,read_orders)

Security notes
- Never commit .env or secrets to source control.
- Replace shops.json with a proper database before production.
- Do not send raw PII to Anthropic; the code only sends sanitized order summaries.
