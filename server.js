// server.js - Shopify App (Express) with OAuth, App Proxy, Anthropic integration.
// Demo store uses shops.json (replace with a DB in production).
import express from 'express';
import crypto from 'crypto';
import fs from 'fs';
import path from 'path';
import dotenv from 'dotenv';
dotenv.config();

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const SHOPIFY_API_KEY = process.env.SHOPIFY_API_KEY;
const SHOPIFY_API_SECRET = process.env.SHOPIFY_API_SECRET;
const HOST = process.env.HOST || '';
const SCOPES = (process.env.SHOPIFY_SCOPES || 'read_products,read_orders').split(',');
const SHOPS_FILE = path.resolve('./shops.json');

const ANTHROPIC_KEY = process.env.ANTHROPIC_API_KEY;
const ANTHROPIC_MODEL = process.env.ANTHROPIC_MODEL || 'claude-haiku-4-5-20251001';
const ANTHROPIC_VERSION = process.env.ANTHROPIC_VERSION || '2023-06-01';

if (!ANTHROPIC_KEY) {
  console.warn('Warning: ANTHROPIC_API_KEY not set. Add it to your environment before deploying.');
}

// Simple file-store for demo. Replace with a DB for production.
function loadShops() {
  try { return JSON.parse(fs.readFileSync(SHOPS_FILE, 'utf8')); } catch { return {}; }
}
function saveShops(data) { fs.writeFileSync(SHOPS_FILE, JSON.stringify(data, null, 2)); }
function getAccessTokenForShop(shop) { const s = loadShops(); return s[shop]?.accessToken; }
function saveAccessToken(shop, token) { const s = loadShops(); s[shop] = { accessToken: token }; saveShops(s); }

// Verify HMAC for OAuth callback / proxy signature
function verifyHmac(query) {
  const { hmac, signature, ...rest } = query; // ignore signature if present
  const message = Object.keys(rest).sort().map(k => `${k}=${rest[k]}`).join('&');
  const digest = crypto.createHmac('sha256', SHOPIFY_API_SECRET).update(message).digest('hex');
  return digest === (hmac || signature);
}

// OAuth install start
app.get('/auth', (req, res) => {
  const { shop } = req.query;
  if (!shop) return res.status(400).send('Missing shop parameter');
  const redirectUri = `${HOST}/auth/callback`;
  const installUrl = `https://${shop}/admin/oauth/authorize?client_id=${SHOPIFY_API_KEY}&scope=${SCOPES.join(',')}&redirect_uri=${encodeURIComponent(redirectUri)}`;
  res.redirect(installUrl);
});

// OAuth callback
app.get('/auth/callback', async (req, res) => {
  try {
    if (!verifyHmac(req.query)) return res.status(400).send('HMAC validation failed');
    const { shop, code } = req.query;
    const tokenRes = await fetch(`https://${shop}/admin/oauth/access_token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_id: SHOPIFY_API_KEY,
        client_secret: SHOPIFY_API_SECRET,
        code
      })
    });
    const tokenJson = await tokenRes.json();
    const accessToken = tokenJson.access_token;
    if (!accessToken) return res.status(400).send('Failed to obtain access token');
    saveAccessToken(shop, accessToken);
    res.send(`App installed on ${shop}. You can close this window.`);
  } catch (err) {
    console.error(err);
    res.status(500).send('OAuth error');
  }
});

// Serve proxied widget JS at /proxy/widget.js
app.get('/proxy/widget.js', (req, res) => {
  if (!verifyHmac(req.query)) return res.status(400).send('Invalid proxy signature');
  const script = `
(function(){
  if (window.ShopAIWidget) return;
  window.ShopAIWidget = true;
  const basePath = '/apps/chatbot';
  const btn = document.createElement('button');
  btn.innerText = 'Chat';
  btn.style = 'position:fixed;right:20px;bottom:20px;z-index:9999;padding:12px 16px;border-radius:24px;background:#111;color:#fff;border:none;cursor:pointer';
  document.body.appendChild(btn);
  const panel = document.createElement('div');
  panel.style = 'position:fixed;right:20px;bottom:70px;width:360px;height:520px;background:#fff;border-radius:8px;box-shadow:0 8px 24px rgba(0,0,0,.15);display:none;flex-direction:column;overflow:hidden;z-index:9999';
  document.body.appendChild(panel);
  panel.innerHTML = '<div style="background:#0a84ff;color:#fff;padding:12px;font-weight:600;display:flex;justify-content:space-between;align-items:center"><div>ShopBot</div><button id="sa-close" style="background:transparent;border:none;color:#fff;font-size:16px;cursor:pointer">✕</button></div><div id="sa-messages" style="flex:1;padding:12px;overflow:auto;background:#f7f9fb"></div><div style="padding:8px;border-top:1px solid #eee;display:flex;"><input id="sa-input" placeholder="Ask about products, orders, shipping..." style="flex:1;padding:8px;border:1px solid #ddd;border-radius:6px;margin-right:8px" /><button id="sa-send" style="padding:8px 12px;border-radius:6px;background:#0a84ff;color:#fff;border:none">Send</button></div>';
  btn.addEventListener('click', ()=> panel.style.display = panel.style.display === 'none' ? 'flex' : 'none');
  panel.querySelector('#sa-close').addEventListener('click', ()=> panel.style.display = 'none');
  const messagesEl = panel.querySelector('#sa-messages');
  const inputEl = panel.querySelector('#sa-input');
  const sendBtn = panel.querySelector('#sa-send');
  function addMessage(text, from='bot'){ const wrapper=document.createElement('div'); wrapper.style='display:flex'; const el=document.createElement('div'); el.style= from==='bot' ? 'background:#fff;padding:10px;border-radius:10px;margin:6px 0;max-width:80%;box-shadow:0 1px 0 rgba(0,0,0,0.04)' : 'margin-left:auto;background:#0a84ff;color:#fff;padding:10px;border-radius:10px;margin:6px 0;max-width:80%'; el.innerText=text; wrapper.appendChild(el); messagesEl.appendChild(wrapper); messagesEl.scrollTop=messagesEl.scrollHeight; }
  async function sendMessage(text, orderInfo) {
    addMessage(text, 'user');
    addMessage('Thinking...', 'bot');
    try {
      const payload = { message: text };
      if (orderInfo) payload.orderLookup = orderInfo;
      const res = await fetch(basePath + '/chat', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await res.json();
      messagesEl.removeChild(messagesEl.lastChild);
      if (data && data.reply) addMessage(data.reply, 'bot'); else addMessage('Sorry, something went wrong.', 'bot');
    } catch (err) {
      messagesEl.removeChild(messagesEl.lastChild);
      addMessage('Network error. Try again later.', 'bot');
      console.error(err);
    }
  }
  sendBtn.addEventListener('click', async ()=> {
    const t = inputEl.value.trim();
    if (!t) return;
    inputEl.value = '';
    if (/\\border\\b|order status|where is my order|order #/i.test(t)) {
      const orderNumber = prompt('Please enter your order number (e.g. #1001):');
      const email = prompt('Please enter the email used for the order:');
      if (!orderNumber || !email) { addMessage('Order lookup cancelled.', 'bot'); return; }
      await sendMessage(t, { orderNumber, email });
    } else {
      await sendMessage(t);
    }
  });
  inputEl.addEventListener('keydown', (e)=> { if (e.key==='Enter') sendBtn.click(); });
  addMessage('Hi! I can help you find products and check order status. Ask me anything.', 'bot');
})();
`;
  res.set('Content-Type', 'application/javascript');
  res.send(script);
});

// Proxied chat endpoint (Shop domain posts via /apps/chatbot/chat)
app.post('/proxy/chat', async (req, res) => {
  if (!verifyHmac(req.query)) return res.status(400).json({ error: 'Invalid proxy signature' });
  const shop = req.query.shop;
  if (!shop) return res.status(400).json({ error: 'Missing shop param' });

  const accessToken = getAccessTokenForShop(shop);
  const { message, orderLookup } = req.body;
  if (!message) return res.status(400).json({ error: 'message required' });

  let orderSummary = '';
  if (orderLookup && accessToken) {
    const { orderNumber, email } = orderLookup;
    try {
      const adminRes = await fetch(`https://${shop}/admin/api/2024-10/orders.json?name=${encodeURIComponent(orderNumber)}`, {
        headers: { 'X-Shopify-Access-Token': accessToken, 'Content-Type': 'application/json' }
      });
      const jr = await adminRes.json();
      const order = jr.orders?.find(o => o.email?.toLowerCase() === (email || '').toLowerCase());
      if (order) {
        orderSummary = `Order ${order.name}: status=${order.financial_status}/${order.fulfillment_status}, total=${order.total_price} ${order.currency}, items=${order.line_items.map(li=>li.title+' x'+li.quantity).join('; ')}.`;
      } else {
        orderSummary = 'Order not found or email does not match.';
      }
    } catch (err) {
      console.error('Order lookup failed', err);
      orderSummary = 'Order lookup failed.';
    }
  }

  const system = { role: 'system', content: `You are a helpful shopping assistant for ${shop}. Keep answers concise.` };
  const userContent = (orderSummary ? `OrderInfo: ${orderSummary}\n\n` : '') + message;
  const user = { role: 'user', content: userContent };
  const messages = [system, user];

  try {
    const anthropicRes = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'x-api-key': ANTHROPIC_KEY,
        'anthropic-version': ANTHROPIC_VERSION,
        'content-type': 'application/json'
      },
      body: JSON.stringify({ model: ANTHROPIC_MODEL, max_tokens: 700, messages })
    });
    const jr = await anthropicRes.json();
    if (!anthropicRes.ok || jr?.type === 'error') {
      console.error('Anthropic API error', jr);
      return res.status(502).json({ error: 'Assistant is temporarily unavailable. Please try again shortly.' });
    }
    const reply = jr?.content?.[0]?.text;
    if (!reply) {
      console.error('Unexpected Anthropic response shape', jr);
      return res.status(502).json({ error: 'Assistant is temporarily unavailable. Please try again shortly.' });
    }
    res.json({ reply: String(reply) });
  } catch (err) {
    console.error(err);
    res.status(500).json({ error: 'LLM error' });
  }
});

// Optional order lookup endpoint
app.post('/proxy/order-lookup', (req, res) => {
  if (!verifyHmac(req.query)) return res.status(400).json({ error: 'Invalid proxy signature' });
  const shop = req.query.shop;
  const token = getAccessTokenForShop(shop);
  if (!token) return res.status(400).json({ error: 'App not installed or missing token' });

  const { orderNumber, email } = req.body;
  if (!orderNumber || !email) return res.status(400).json({ error: 'orderNumber and email required' });

  (async () => {
    try {
      const adminRes = await fetch(`https://${shop}/admin/api/2024-10/orders.json?name=${encodeURIComponent(orderNumber)}`, {
        headers: { 'X-Shopify-Access-Token': token, 'Content-Type': 'application/json' }
      });
      const jr = await adminRes.json();
      const order = jr.orders?.find(o => o.email?.toLowerCase() === (email || '').toLowerCase());
      if (!order) return res.status(404).json({ error: 'order not found or email mismatch' });
      const safe = {
        name: order.name,
        created_at: order.created_at,
        financial_status: order.financial_status,
        fulfillment_status: order.fulfillment_status,
        total_price: order.total_price,
        currency: order.currency,
        items: order.line_items.map(li => ({ title: li.title, qty: li.quantity }))
      };
      res.json({ order: safe });
    } catch (err) {
      console.error(err);
      res.status(500).json({ error: 'lookup failed' });
    }
  })();
});

const port = process.env.PORT || 3000;
app.listen(port, ()=> console.log(`App listening on ${port}`));
