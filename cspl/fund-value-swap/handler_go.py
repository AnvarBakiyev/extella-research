
def execute(source,extra):
 import os,subprocess,shutil,json,hashlib
 from pathlib import Path
 compiler=shutil.which('go') or next((x for x in ('/opt/homebrew/bin/go','/usr/local/go/bin/go') if Path(x).is_file()),None)
 if not compiler:raise RuntimeError('Go compiler is not installed on this device')
 if not source.endswith(chr(10)):source+=chr(10)
 digest=hashlib.sha256(source.encode()).hexdigest();folder=Path.home()/'.extella'/'opyt16go'/digest;folder.mkdir(parents=True,exist_ok=True)
 env=dict(os.environ);env.update({'GOCACHE':str(folder.parent/'cache'),'GOPATH':str(folder.parent/'path'),'GOTELEMETRY':'off','GOTOOLCHAIN':'local','CGO_ENABLED':'0','HOME':str(Path.home())})
 binary=folder/'program'
 if not binary.exists():
  (folder/'program.go').write_text(source)
  built=subprocess.run([compiler,'build','-o',str(binary),str(folder/'program.go')],capture_output=True,text=True,env=env,cwd=folder,timeout=180)
  if built.returncode:raise RuntimeError('Go compilation failed: '+built.stderr[-600:])
 params={k:v for k,v in extra.items() if isinstance(v,(str,int,float))}
 run=subprocess.run([str(binary)],input=json.dumps(params),capture_output=True,text=True,timeout=600)
 if run.returncode:raise RuntimeError('Go program failed: '+run.stderr[-300:])
 return json.loads(run.stdout)
