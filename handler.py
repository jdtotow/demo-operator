import kopf, kubernetes

prom_volume = open('/prom-volume.json','r')

@kopf.on.resume('unipi.gr', 'v1', 'triplemonitoringengines')
@kopf.on.create('unipi.gr', 'v1', 'triplemonitoringengines')
def create_fn(body, spec, **kwargs):
    name = body['metadata']['name']
    namespace = body['metadata']['namespace']
    _type = spec['type']

    # Pod template
    pod = {'apiVersion': 'v1', 'metadata': {'name' : name, 'labels': {'app': 'tme'}}}

    # Service template
    svc = {'apiVersion': 'v1', 'metadata': {'name' : name}, 'spec': { 'selector': {'app': 'tme'}, 'type': 'ClusterIP'}}

    if _type == 'prometheus':
      image = 'prom/prometheus'
      port = 9090
      args = ['--config.file=/etc/prometheus/prometheus.yml','--storage.tsdb.path=/prometheus','--web.console.libraries=/etc/prometheus/console_libraries','--storage.tsdb.retention.time=48h','--web.console.templates=/etc/prometheus/consoles','--web.enable-lifecycle']
      pod['spec'] = { 'containers': [ { 'image': image, 'name': _type, 'args': args,'volumeMounts': prom_volume['volumeMounts'] } ],'volumes': prom_volume['volumes']}
      pod['spec']['initContainers'] = [{"name": "prometheus-config-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/config"],"volumeMounts": [{"name": "config-volume","mountPath": "/config"}]},{"name": "prometheus-tsdb-permission-fix","image": "busybox","command": ["/bin/chmod","-R","777","/tsdb"],"volumeMounts": [{"name": "prometheus-tsdb","mountPath": "/tsdb"}]}]
      svc['spec']['ports'] = [{ 'port': port, 'targetPort': port}]

    if _type == 'grafana':
      image = 'grafana/grafana'
      port = 3000
      pod['spec'] = { 'containers': [ { 'image': image, 'name': _type } ]}
      svc['spec']['ports'] = [{ 'port': port, 'targetPort': port}]

    # Make the Pod and Service the children of the TME object
    kopf.adopt(pod, owner=body)
    kopf.adopt(svc, owner=body)

    # Communication with the API Server
    api = kubernetes.client.CoreV1Api()

    # Create Pod
    obj = api.create_namespaced_pod(namespace, pod)
    print(f"Pod {obj.metadata.name} created")

    # Create Service
    obj = api.create_namespaced_service(namespace, svc)
    print(f"ClusterIP Service {obj.metadata.name} created, exposing on port {obj.spec.ports[0].node_port}")

    # Update status
    msg = f"Pod and Service created by Database {name}"
    return {'message': msg}

@kopf.on.delete('unipi.gr', 'v1', 'triplemonitoringengines')
def delete(body, **kwargs):
    msg = f"Database {body['metadata']['name']} and its Pod / Service children deleted"
    return {'message': msg}
