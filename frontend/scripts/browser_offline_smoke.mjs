const DEBUG_URL = process.env.CDP_URL || 'http://127.0.0.1:9222';
const APP_URL = process.env.APP_URL || 'http://127.0.0.1:4173';
const TEST_IMAGE = process.env.TEST_IMAGE || 'D:\\Projects\\AI_MAIZE_DISEASE_SYSTEM\\ml_model\\dataset\\test\\Healthy\\Corn_Health (1003).jpg';

async function waitForTarget() {
  for (let attempt = 0; attempt < 30; attempt += 1) {
    try {
      const targets = await (await fetch(`${DEBUG_URL}/json/list`)).json();
      const page = targets.find((target) => target.type === 'page' && target.url.startsWith(APP_URL));
      if (page) return page;
    } catch {
      // Edge is still starting.
    }
    await new Promise((resolve) => setTimeout(resolve, 1000));
  }
  throw new Error(`Could not connect to the page at ${APP_URL}.`);
}

const target = await waitForTarget();
const socket = new WebSocket(target.webSocketDebuggerUrl);
await new Promise((resolve, reject) => {
  socket.addEventListener('open', resolve, { once: true });
  socket.addEventListener('error', reject, { once: true });
});

let nextId = 0;
const pending = new Map();
const loadWaiters = [];
const requestUrls = [];
socket.addEventListener('message', (event) => {
  const message = JSON.parse(event.data);
  if (message.method === 'Page.loadEventFired') loadWaiters.splice(0).forEach((resolve) => resolve());
  if (message.method === 'Network.requestWillBeSent') requestUrls.push(message.params.request.url);
  if (message.id && pending.has(message.id)) {
    const { resolve, reject } = pending.get(message.id);
    pending.delete(message.id);
    if (message.error) reject(new Error(message.error.message));
    else resolve(message.result);
  }
});

function cdp(method, params = {}) {
  const id = ++nextId;
  return new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
    socket.send(JSON.stringify({ id, method, params }));
  });
}

async function evaluate(expression) {
  const response = await cdp('Runtime.evaluate', {
    expression,
    awaitPromise: true,
    returnByValue: true,
    userGesture: true,
  });
  if (response.exceptionDetails) {
    throw new Error(response.exceptionDetails.exception?.description || response.exceptionDetails.text);
  }
  return response.result.value;
}

async function waitForLoad() {
  const loaded = new Promise((resolve) => loadWaiters.push(resolve));
  await loaded;
}

async function navigate(url) {
  const loaded = waitForLoad();
  await cdp('Page.navigate', { url });
  await loaded;
}

async function waitForText(text, timeoutMs = 30000) {
  const started = Date.now();
  while (Date.now() - started < timeoutMs) {
    const present = await evaluate(`(document.body?.innerText || '').toLowerCase().includes(${JSON.stringify(text.toLowerCase())})`);
    if (present) return;
    await new Promise((resolve) => setTimeout(resolve, 300));
  }
  const pageState = await evaluate(`({ url: location.href, readyState: document.readyState, body: document.body?.innerText, fileInputs: [...(document.querySelectorAll('input[type="file"]') || [])].map(input => ({ accept: input.accept, capture: input.capture, files: input.files?.length })), buttons: [...document.querySelectorAll('button')].map(button => button.textContent?.trim()) })`);
  throw new Error(`Timed out waiting for page text: ${text}; page state: ${JSON.stringify(pageState)}`);
}

await cdp('Page.enable');
await cdp('Runtime.enable');
await cdp('Network.enable');
await cdp('DOM.enable');
await cdp('Network.setCacheDisabled', { cacheDisabled: true });
await cdp('Network.emulateNetworkConditions', {
  offline: false,
  latency: 0,
  downloadThroughput: -1,
  uploadThroughput: -1,
  connectionType: 'wifi',
});

await evaluate("sessionStorage.setItem('maizecare_route_preview_role', 'farmer')");
await navigate(APP_URL);
await navigate(`${APP_URL}/farmer/diagnose`);
await waitForText('Diagnose on this device');

await evaluate(`(async()=>{
  await navigator.serviceWorker.ready;
  return true;
})()`);
for (let attempt = 0; attempt < 3; attempt += 1) {
  if (await evaluate('Boolean(navigator.serviceWorker.controller)')) break;
  await navigate(`${APP_URL}/farmer/diagnose`);
}

let documentInfo = await cdp('DOM.getDocument', { depth: -1 });
let inputQuery = await cdp('DOM.querySelector', {
  nodeId: documentInfo.root.nodeId,
  selector: 'input[type="file"]',
});
if (!inputQuery.nodeId) throw new Error('The diagnosis page file input was not found.');
await cdp('DOM.setFileInputFiles', { nodeId: inputQuery.nodeId, files: [TEST_IMAGE] });
await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.includes('Diagnose on this device'))?.click()`);
await waitForText('On-device model result');

const onlineResult = await evaluate(`(async()=>{
  const modelCache = await caches.open('maizecare-maize-model-v1');
  const shellCache = await caches.open('maizecare-shell-v1');
  return {
    resultVisible: document.body.innerText.toLowerCase().includes('on-device model result'),
    localOnly: document.body.innerText.includes('Local only'),
    modelReady: document.body.innerText.includes('Downloaded and ready'),
    controlling: Boolean(navigator.serviceWorker.controller),
    modelFiles: (await modelCache.keys()).map(request => new URL(request.url).pathname.split('/').pop()),
    shellAssetCount: (await shellCache.keys()).length,
  };
})()`);
if (!onlineResult.resultVisible || !onlineResult.localOnly || onlineResult.modelFiles.length < 2) {
  throw new Error(`The online local-inference setup did not complete: ${JSON.stringify(onlineResult)}`);
}

await cdp('Network.emulateNetworkConditions', {
  offline: true,
  latency: 0,
  downloadThroughput: 0,
  uploadThroughput: 0,
  connectionType: 'none',
});
const loaded = waitForLoad();
await cdp('Page.reload', { ignoreCache: true });
await loaded;
await waitForText('Diagnose on this device');

documentInfo = await cdp('DOM.getDocument', { depth: -1 });
inputQuery = await cdp('DOM.querySelector', {
  nodeId: documentInfo.root.nodeId,
  selector: 'input[type="file"]',
});
await cdp('DOM.setFileInputFiles', { nodeId: inputQuery.nodeId, files: [TEST_IMAGE] });
await evaluate(`[...document.querySelectorAll('button')].find(button => button.textContent.includes('Diagnose on this device'))?.click()`);
await waitForText('On-device model result');

const offlineResult = await evaluate(`(async()=>({
  resultVisible: document.body.innerText.toLowerCase().includes('on-device model result'),
  localOnly: document.body.innerText.includes('Local only'),
  offlineIndicator: document.body.innerText.includes('Offline Mode'),
  modelReady: document.body.innerText.includes('Downloaded and ready'),
  controlling: Boolean(navigator.serviceWorker.controller),
  predictionText: document.querySelector('section[aria-live="polite"] h2')?.textContent?.trim(),
}))()`);
if (!offlineResult.resultVisible || !offlineResult.localOnly || !offlineResult.offlineIndicator) {
  throw new Error(`Offline diagnosis did not complete: ${JSON.stringify(offlineResult)}`);
}

const diagnosisApiRequests = requestUrls.filter((url) => /\/api\/diagnosis\/complete/.test(url));
console.log(JSON.stringify({ onlineResult, offlineResult, diagnosisApiRequests }, null, 2));
socket.close();
