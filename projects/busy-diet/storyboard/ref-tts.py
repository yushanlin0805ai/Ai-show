import msgpack,urllib.request,urllib.error,sys
ref,reftext,text,out=sys.argv[1:5]
body={"text":open(text,encoding='utf-8').read().strip(),"references":[{"audio":open(ref,'rb').read(),"text":open(reftext,encoding='utf-8').read().strip()}],
"format":"mp3","mp3_bitrate":192,"normalize":True,"language":"zh-TW","prosody":{"speed":1.0}}
req=urllib.request.Request("https://api.fish.audio/v1/tts",data=msgpack.packb(body),headers={"Content-Type":"application/msgpack","model":"s2.1-pro-free"},method="POST")
try:
  d=urllib.request.urlopen(req,timeout=300).read()
except urllib.error.HTTPError as e:
  sys.exit(f"{e.code} {e.read()[:300]}")
open(out,'wb').write(d); print(out,len(d))
