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
python3 - <<'PY'
import base64, json, os, pathlib, subprocess
name='clipscout-editorial'
ns='team-32'
def apply(obj):
    subprocess.run(['kubectl','-n',ns,'apply','-f','-'], input=json.dumps(obj).encode(), check=True)
def meta(suffix=''):
    return {'name':name+suffix,'namespace':ns,'labels':{'app':name,'app.kubernetes.io/managed-by':'clipscout'}}
apply({'apiVersion':'v1','kind':'ConfigMap','metadata':meta('-code'),
       'data':{n:pathlib.Path(n).read_text() for n in ['main.py','index.html']}})
# The workshop ingress hostname resolves on the VM, but not in pod DNS.
# Resolve the existing VSS service; do not change the shared VSS deployment.
service=json.loads(subprocess.check_output(['kubectl','-n',ns,'get','service','video-backend-service','-o','json']))
internal_url='http://'+service['metadata']['name']+':'+str(service['spec']['ports'][0]['port'])
credentials={'VSS_URL':internal_url,'VSS_USERNAME':os.environ['USERNAME'],'VSS_PASSWORD':os.environ['PASSWORD']}
apply({'apiVersion':'v1','kind':'Secret','metadata':meta('-vss'),'type':'Opaque',
       'data':{k:base64.b64encode(v.encode()).decode() for k,v in credentials.items()}})
apply({'apiVersion':'apps/v1','kind':'Deployment','metadata':meta(),
       'spec':{'replicas':1,'selector':{'matchLabels':{'app':name}},
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
kubectl -n team-32 rollout status deployment/clipscout-editorial --timeout=55s
