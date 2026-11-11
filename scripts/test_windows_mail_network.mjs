// Test the shipped bridge with isolated identities, using production discovery.
// Does not load the user's state.json, credentials, peer code, or letters.
import { spawn } from 'node:child_process';
import { randomBytes, randomUUID } from 'node:crypto';
import { mkdtemp, readFile, readdir, rm, writeFile } from 'node:fs/promises';
import { createInterface } from 'node:readline';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
const project = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const directory = path.resolve(process.argv[2] || path.join(project, 'build/Meow-Windows-MacUI/mailbridge'));
const output = path.join(project, 'build/mail-network-results.json');
const temp = await mkdtemp(path.join(tmpdir(), 'meow-network-check-'));
const log = [], clients = [];
function report(name, detail) { log.push({ name, detail, at: new Date().toISOString() }); console.log(name + ': ' + detail); }
function client(name) {
  const child = spawn(path.join(directory, 'node.exe'), [path.join(directory, 'bridge.mjs')], { windowsHide: true, stdio: ['pipe', 'pipe', 'pipe'] });
  const pending = new Map(); let sequence = 0;
  createInterface({ input: child.stdout }).on('line', line => { const m = JSON.parse(line); const p = pending.get(m.id); if (p) { clearTimeout(p.timer); pending.delete(m.id); m.error ? p.reject(new Error(m.error)) : p.resolve(m.result); } });
  child.stderr.resume();
  child.on('error', error => { for (const p of pending.values()) p.reject(error); });
  child.on('exit', () => { for (const p of pending.values()) { clearTimeout(p.timer); p.reject(new Error(name + ' bridge exited')); } pending.clear(); });
  const api = { child, call(message) { const id = ++sequence; return new Promise((resolve, reject) => { const timer = setTimeout(() => { pending.delete(id); reject(new Error(name + ' RPC timeout after 40 seconds')); }, 40000); pending.set(id, { resolve, reject, timer }); child.stdin.write(JSON.stringify({ ...message, id }) + '\n'); }); } };
  clients.push(api); return api;
}
try {
  const a = client('A'), b = client('B');
  const [first, second] = await Promise.all([a.call({ op: 'init', key: randomBytes(32).toString('base64'), inbox: path.join(temp, 'a'), localOnly: false }), b.call({ op: 'init', key: randomBytes(32).toString('base64'), inbox: path.join(temp, 'b'), localOnly: false })]);
  await Promise.all([a.call({ op: 'peer', code: second.code }), b.call({ op: 'peer', code: first.code })]);
  report('PASS', 'Two production-mode temporary mailboxes initialized and paired');
  for (const [sender, recipient, from, to, folder] of [[a, b, first, second, 'b'], [b, a, second, first, 'a']]) {
    const letter = { id: randomUUID(), senderID: from.deviceID, recipientID: to.deviceID, body: '隔离公网发现测试：你好小喵 💌', createdAt: new Date().toISOString() };
    let receipt; for (let attempt = 0; attempt < 3; attempt++) { try { receipt = await sender.call({ op: 'send', letter }); break; } catch (error) { if (attempt === 2) throw error; report('RETRY', 'Discovery not ready: ' + error.message); await new Promise(resolve => setTimeout(resolve, 10000)); } }
    if (receipt.letterID !== letter.id) throw new Error('Receipt id mismatch');
    const files = await readdir(path.join(temp, folder));
    const saved = JSON.parse(await readFile(path.join(temp, folder, files.find(f => f === letter.id + '.json')), 'utf8'));
    if (saved.letter.body !== letter.body) throw new Error('Saved content mismatch');
    report('PASS', 'Production device-code discovery, transfer and durable receipt to ' + folder.toUpperCase());
  }
} catch (error) { report('FAIL', error.message); process.exitCode = 1; }
finally {
  for (const c of clients) c.child.stdin.end();
  await Promise.all(clients.map(c => new Promise(resolve => { if (c.child.exitCode !== null) return resolve(); const timer = setTimeout(() => { c.child.kill(); resolve(); }, 1500); c.child.once('exit', () => { clearTimeout(timer); resolve(); }); })));
  await rm(temp, { recursive: true, force: true });
  await writeFile(output, JSON.stringify({ scope: 'isolated same-host production discovery; not a real Windows-to-Mac delivery test', log }, null, 2));
}
