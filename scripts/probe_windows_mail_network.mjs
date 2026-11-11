import { Endpoint } from '../windows/Meow.MailBridge/node_modules/@number0/iroh/index.js';
const builder = Endpoint.builder(); builder.applyN0(); const endpoint = await builder.bind();
let timer;
try { await Promise.race([endpoint.online(), new Promise((_, reject) => { timer = setTimeout(() => reject(new Error('home relay unavailable after 20 seconds')), 20000); })]); console.log('PASS home relay online'); }
catch (error) { console.log('FAIL ' + error.message); process.exitCode = 1; }
finally { clearTimeout(timer); console.log(JSON.stringify({hasRelay:!!endpoint.addr().relayUrl(),directAddressCount:endpoint.addr().directAddresses().length})); await endpoint.close(); }
