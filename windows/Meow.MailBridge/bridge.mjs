import { Endpoint, EndpointAddr, EndpointId, EndpointTicket } from '@number0/iroh';
import { createInterface } from 'node:readline';
import { mkdir, readFile, writeFile, rename } from 'node:fs/promises';
import path from 'node:path';
let ep, peer, root, generation=0, active = new Set();
const alpn = [...Buffer.from('meow/mail/1')];
const encode = v => [...Buffer.from(JSON.stringify(v))];
const idOf = ep => ep.id().toString();
function code(address) { return 'meow1:' + Buffer.from(JSON.stringify({version:1,deviceID:address.id().toString(),ticket:EndpointTicket.fromAddr(address).toString()})).toString('base64url'); }
function decodeCode(code) {
  if(typeof code!=='string'||!code.startsWith('meow1:')||code.length>14000)throw Error('设备码无效');
  const card=JSON.parse(Buffer.from(code.slice(6),'base64url'));
  if(card.version!==1||!(/^[0-9a-f]{64}$/).test(card.deviceID))throw Error('设备码版本或身份无效');
  const address=EndpointTicket.fromString(card.ticket).endpointAddr();
  if(address.id().toString()!==card.deviceID||card.deviceID===idOf(ep))throw Error('设备码身份不匹配');
  return card;
}
function validate(letter,remote,local) {
  if(!letter||letter.senderID!==remote||letter.recipientID!==local||!(/^[0-9a-f-]{36}$/i).test(letter.id)||typeof letter.body!=='string'||!letter.body.trim()||[...letter.body].length>5000||Buffer.byteLength(letter.body)>16384||!Number.isFinite(Date.parse(letter.createdAt)))throw Error('信件内容或身份无效');
}
async function accept(incoming) {
  if(!peer||active.size>=4){await incoming.refuse();return;}
  let conn;
  try {
    conn=await (await incoming.accept()).connect();active.add(conn);
    const expected=peer.deviceID, revision=generation;
    if(conn.remoteId().toString()!==expected)throw Error('未绑定设备');
    const timeout=setTimeout(()=>conn.close(2n,[]),25000);
    try {
      const stream=await conn.acceptBi();const packet=JSON.parse(Buffer.from(await stream.recv.readToEnd(32768)));
      if(packet.version!==1||packet.kind!=='letter'||peer?.deviceID!==expected)throw Error('协议不匹配');
      const letter=packet.letter;validate(letter,expected,idOf(ep));
      const file=path.join(root,letter.id.toLowerCase()+'.json');
      let saved;
      try{saved=JSON.parse(await readFile(file,'utf8'));}catch(e){if(e.code!=='ENOENT')throw e;}
      if(saved&&(saved.letter.senderID!==letter.senderID||saved.letter.recipientID!==letter.recipientID||saved.letter.body!==letter.body))throw Error('重复ID内容不一致');
      if(revision!==generation)throw Error('绑定已变化');
      if(!saved){saved={letter,receivedAt:new Date().toISOString().replace(/\.\d{3}Z$/,'Z')};const temp=file+'.tmp';await writeFile(temp,JSON.stringify(saved));if(revision!==generation)throw Error('绑定已变化');await rename(temp,file);}
      const receipt={letterID:letter.id,senderID:letter.senderID,recipientID:letter.recipientID,receivedAt:saved.receivedAt};
      await stream.send.writeAll(encode({version:1,kind:'receipt',receipt,senderTicket:EndpointTicket.fromAddr(ep.addr()).toString()}));await stream.send.finish();await conn.closed();
    }finally{clearTimeout(timeout);}
  }catch{}finally{if(conn){active.delete(conn);conn.close(0n,[]);}}
}
async function command(m) {
  if(m.op==='init') {
    if(ep)throw Error('已经启动');root=m.inbox;await mkdir(root,{recursive:true});
    const builder=Endpoint.builder();if(m.localOnly)builder.applyMinimal();else builder.applyN0();
    builder.secretKey([...Buffer.from(m.key,'base64')]);builder.alpns([alpn]);if(m.localOnly)builder.bindAddr('127.0.0.1:0');ep=await builder.bind();
    (async()=>{while(ep&&!ep.isClosed()){const next=await ep.acceptNext();if(!next)break;void accept(next);}})().catch(()=>{});
    return {deviceID:idOf(ep),code:code(m.localOnly?ep.addr():new EndpointAddr(ep.id()))};
  }
  if(!ep)throw Error('信箱未启动');
  if(m.op==='peer'){peer=m.code?decodeCode(m.code):null;generation++;for(const c of active)c.close(1n,[]);return peer;}
  if(m.op==='send') {
    if(!peer)throw Error('请先绑定另一台设备');const target=peer;validate(m.letter,idOf(ep),target.deviceID);
    let conn;const timer=setTimeout(()=>conn?.close(2n,[]),25000);
    try {
      conn=await ep.connect(EndpointTicket.fromString(target.ticket).endpointAddr(),alpn);active.add(conn);
      if(peer?.deviceID!==target.deviceID||conn.remoteId().toString()!==target.deviceID)throw Error('绑定已变化');
      const stream=await conn.openBi();const packet={version:1,kind:'letter',letter:m.letter,senderTicket:EndpointTicket.fromAddr(ep.addr()).toString()};
      if(Buffer.byteLength(JSON.stringify(packet))>32768)throw Error('信件过大');await stream.send.writeAll(encode(packet));await stream.send.finish();
      const response=JSON.parse(Buffer.from(await stream.recv.readToEnd(32768)));const receipt=response.receipt;
      if(response.version!==1||response.kind!=='receipt'||receipt?.letterID.toLowerCase()!==m.letter.id.toLowerCase()||receipt.senderID!==m.letter.senderID||receipt.recipientID!==m.letter.recipientID)throw Error('没有收到有效保存回执');return receipt;
    }finally{clearTimeout(timer);if(conn){active.delete(conn);conn.close(0n,[]);}}
  }
  throw Error('未知操作');
}
createInterface({input:process.stdin}).on('line',line=>{
  let m;try{if(line.length>70000)throw Error();m=JSON.parse(line);}catch{return;}
  command(m).then(result=>process.stdout.write(JSON.stringify({id:m.id,result})+'\n'),e=>process.stdout.write(JSON.stringify({id:m.id,error:e.message})+'\n'));
}).on('close',async()=>{await ep?.close();process.exit(0);});
