#!/usr/bin/env bash
set -euo pipefail
mapfile -t configs < <(find /config -maxdepth 1 -type f -name '*.config' | sort)
[[ ${#configs[@]} -eq 1 ]] || { echo 'Expected one team config'; exit 1; }
set -a
source "${configs[0]}"
set +a
[[ "$USERNAME" == 'team-32' ]] || { echo 'Unexpected team namespace'; exit 1; }
export KUBECONFIG=/config/team-32-k8s.yaml
cd "$(dirname "$0")"
# Keep a VM-side backup before replacing this app's temporary volume.
backup_dir="$HOME/.local/state/clipscout"
mkdir -p "$backup_dir"
if kubectl -n team-32 get deployment clipscout-editorial >/dev/null 2>&1; then
  kubectl -n team-32 exec deployment/clipscout-editorial -- tar -czf - -C /data . > "$backup_dir/app-data.tmp.tgz"
  mv "$backup_dir/app-data.tmp.tgz" "$backup_dir/app-data.tgz"
fi
python3 - <<'PY'
import base64, json, os, pathlib, subprocess
name='clipscout-editorial'
ns='team-32'
def apply(obj):
    subprocess.run(['kubectl','-n',ns,'apply','-f','-'], input=json.dumps(obj).encode(), check=True)
def meta(suffix=''):
    return {'name':name+suffix,'namespace':ns,'labels':{'app':name,'app.kubernetes.io/managed-by':'clipscout'}}
apply({'apiVersion':'v1','kind':'ConfigMap','metadata':meta('-code'),
       'data':{n:pathlib.Path(n).read_text() for n in ['main.py','index.html','editorial_advisor.py']}})
# The workshop ingress hostname resolves on the VM, but not in pod DNS.
# Resolve the existing VSS service; do not change the shared VSS deployment.
service=json.loads(subprocess.check_output(['kubectl','-n',ns,'get','service','video-backend-service','-o','json']))
internal_url='http://'+service['metadata']['name']+':'+str(service['spec']['ports'][0]['port'])
credentials={'VSS_URL':internal_url,'VSS_USERNAME':os.environ['USERNAME'],'VSS_PASSWORD':os.environ['PASSWORD']}
if os.environ.get('WANDB_API_KEY'):
    credentials['WANDB_API_KEY']=os.environ['WANDB_API_KEY']
for key in ('WANDB_INFERENCE_MODEL','WANDB_INFERENCE_BASE_URL','WANDB_INFERENCE_PROJECT'):
    if os.environ.get(key): credentials[key]=os.environ[key]
if 'WANDB_INFERENCE_PROJECT' not in credentials and os.environ.get('WANDB_TEAM') and os.environ.get('WANDB_PROJECT'):
    credentials['WANDB_INFERENCE_PROJECT']=os.environ['WANDB_TEAM']+'/'+os.environ['WANDB_PROJECT']
apply({'apiVersion':'v1','kind':'Secret','metadata':meta('-vss'),'type':'Opaque',
       'data':{k:base64.b64encode(v.encode()).decode() for k,v in credentials.items()}})
apply({'apiVersion':'apps/v1','kind':'Deployment','metadata':meta(),
       'spec':{'replicas':1,'strategy':{'type':'Recreate'},'selector':{'matchLabels':{'app':name}},
               'template':{'metadata':{'labels':{'app':name}},'spec':{
                 'containers':[{'name':'app','image':'python:3.12-slim','imagePullPolicy':'IfNotPresent',
                   'workingDir':'/code','ports':[{'containerPort':8080}],
                   'envFrom':[{'secretRef':{'name':name+'-vss'}}],
                   'env':[{'name':'PORT','value':'8080'},{'name':'DATA_DIR','value':'/data'},
                          {'name':'PYTHONUNBUFFERED','value':'1'},{'name':'PYTHONDONTWRITEBYTECODE','value':'1'}],
                   'command':['bash','-c'],
                   'args':['set -e; apt-get update -qq; apt-get install -y -qq --no-install-recommends ffmpeg >/tmp/apt-install.log 2>&1; exec python main.py'],
                   'volumeMounts':[{'name':'code','mountPath':'/code','readOnly':True},{'name':'data','mountPath':'/data'}],
                   'resources':{'requests':{'cpu':'200m','memory':'256Mi'},'limits':{'cpu':'2','memory':'1Gi'}},
                   'startupProbe':{'httpGet':{'path':'/health','port':8080},'periodSeconds':5,'failureThreshold':60},
                   'readinessProbe':{'httpGet':{'path':'/health','port':8080},'periodSeconds':5}}],
                 'volumes':[{'name':'code','configMap':{'name':name+'-code'}},{'name':'data','emptyDir':{'sizeLimit':'1Gi'}}]}}}})
apply({'apiVersion':'v1','kind':'Service','metadata':meta(),
       'spec':{'selector':{'app':name},'ports':[{'port':80,'targetPort':8080}]}})
apply({'apiVersion':'networking.k8s.io/v1','kind':'Ingress','metadata':{
          **meta(),'annotations':{'nginx.ingress.kubernetes.io/rewrite-target':'/$2',
             'nginx.ingress.kubernetes.io/use-regex':'true','nginx.ingress.kubernetes.io/proxy-read-timeout':'180'}},
       'spec':{'ingressClassName':'nginx','rules':[{'host':'video-lab-team-32.cosmos.vastdata.com',
          'http':{'paths':[{'path':'/app(/|$)(.*)','pathType':'ImplementationSpecific',
             'backend':{'service':{'name':name,'port':{'number':80}}}}]}}]}})
PY
kubectl -n team-32 rollout restart deployment/clipscout-editorial
ready=false
for attempt in 1 2 3; do
  if kubectl -n team-32 rollout status deployment/clipscout-editorial --timeout=55s; then
    ready=true
    break
  fi
done
[[ "$ready" == true ]] || { echo "App rollout incomplete; backup retained at $backup_dir/app-data.tgz"; exit 1; }
if [[ -f "$backup_dir/app-data.tgz" ]]; then
  kubectl -n team-32 exec -i deployment/clipscout-editorial -- tar -xzf - -C /data < "$backup_dir/app-data.tgz"
  kubectl -n team-32 exec deployment/clipscout-editorial -- python -c 'import os,signal; os.kill(1,signal.SIGHUP)'
  echo 'Restored ClipScout catalog and exports from the VM backup.'
fi
