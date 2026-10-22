"""Helm rendering contracts; needs Helm and PyYAML, no cluster required."""
import os
from pathlib import Path
import shutil
import subprocess
import unittest

try:
    import yaml
except ImportError:
    yaml = None

HELM = os.environ.get('HELM_BIN') or shutil.which('helm')
CHART = Path(__file__).resolve().parents[1] / 'charts/ontop'


@unittest.skipUnless(HELM and yaml, 'Requires Helm (or HELM_BIN) and PyYAML')
class HelmChartTests(unittest.TestCase):
    def render(self, *args):
        result = subprocess.run([HELM, 'template', 'faostat', str(CHART),
                                 '--namespace', 'provider',
                                 '-f', str(CHART.parents[1] / 'examples/faostat.yaml'), *args], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        return {doc['kind']: doc for doc in yaml.safe_load_all(result.stdout) if doc}

    def test_default_read_only_deployment_and_service(self):
        docs = self.render()
        self.assertEqual(set(docs), {'Deployment', 'Service', 'Pod'})
        deployment = docs['Deployment']
        pod = deployment['spec']['template']['spec']
        container = pod['containers'][0]
        self.assertEqual(container['image'], 'provider/sparql-faostat-ontop:0.0.1')
        self.assertEqual(container['imagePullPolicy'], 'IfNotPresent')
        self.assertTrue(container['securityContext']['readOnlyRootFilesystem'])
        self.assertEqual(pod['securityContext']['runAsUser'], 999)
        self.assertFalse(pod['automountServiceAccountToken'])
        self.assertEqual(container['volumeMounts'], [{'name': 'tmp', 'mountPath': '/tmp'}])
        self.assertEqual(pod['volumes'], [{'name': 'tmp', 'emptyDir': {'sizeLimit': '1Gi'}}])
        self.assertIn('startupProbe', container)
        self.assertIn('readinessProbe', container)
        self.assertIn('livenessProbe', container)
        self.assertEqual(docs['Service']['spec']['selector'], deployment['spec']['selector']['matchLabels'])
        self.assertEqual(docs['Service']['spec']['ports'][0]['targetPort'], 'http')
        self.assertEqual(docs['Pod']['metadata']['annotations']['helm.sh/hook'], 'test')

    def test_ingress_tls_and_custom_service_port(self):
        docs = self.render('--set', 'ingress.enabled=true', '--set', 'ingress.className=nginx',
                           '--set', 'ingress.hosts[0].host=faostat.example.org',
                           '--set', 'ingress.hosts[0].paths[0].path=/',
                           '--set', 'ingress.hosts[0].paths[0].pathType=Prefix',
                           '--set', 'ingress.tls[0].secretName=faostat-tls',
                           '--set', 'ingress.tls[0].hosts[0]=faostat.example.org',
                           '--set', 'service.port=8090')
        ingress = docs['Ingress']['spec']
        self.assertEqual(ingress['ingressClassName'], 'nginx')
        self.assertEqual(ingress['tls'][0]['secretName'], 'faostat-tls')
        backend = ingress['rules'][0]['http']['paths'][0]['backend']['service']
        self.assertEqual(backend['name'], docs['Service']['metadata']['name'])
        self.assertEqual(backend['port']['number'], 8090)

    def test_digest_precedence_and_recreate_strategy(self):
        digest = 'sha256:' + 'a' * 64
        docs = self.render('--set', 'image.digest=' + digest,
                           '--set', 'strategy.type=Recreate', '--set', 'replicaCount=2')
        spec = docs['Deployment']['spec']
        self.assertEqual(spec['replicas'], 2)
        self.assertEqual(spec['strategy'], {'type': 'Recreate'})
        self.assertEqual(spec['template']['spec']['containers'][0]['image'],
                         'provider/sparql-faostat-ontop@' + digest)
        self.assertEqual(docs['Pod']['spec']['containers'][0]['image'],
                         'provider/sparql-faostat-ontop@' + digest)

    def test_explicit_image_is_required(self):
        result = subprocess.run([HELM, 'template', 'ontop', str(CHART)],
                                capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('image', result.stderr)

    def test_tiva_example_and_independent_releases(self):
        docs = self.render('-f', str(CHART.parents[1] / 'examples/tiva.yaml'))
        self.assertEqual(docs['Deployment']['spec']['template']['spec']['containers'][0]['image'],
                         'registry.example.org/provider/sparql-tiva-ontop:REPLACE_WITH_IMAGE_TAG')
        result = subprocess.run([HELM, 'template', 'tiva', str(CHART),
                                 '-f', str(CHART.parents[1] / 'examples/tiva.yaml')],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        tiva = {d['kind']: d for d in yaml.safe_load_all(result.stdout) if d}
        self.assertEqual(tiva['Service']['metadata']['name'], 'tiva-ontop')
        self.assertEqual(tiva['Deployment']['spec']['selector']['matchLabels']['app.kubernetes.io/instance'],
                         'tiva')

    def test_reject_invalid_values(self):
        for value in ['replicaCount=-1', 'service.port=0', 'image.digest=sha256:bad',
                      'env.ONTOP_LOG_LEVEL=true', 'image.pullPolicy=sometimes']:
            with self.subTest(value=value):
                result = subprocess.run([HELM, 'template', 'faostat', str(CHART),
                                        '-f', str(CHART.parents[1] / 'examples/faostat.yaml'), '--set', value],
                                        capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('schema', result.stderr.lower())


if __name__ == '__main__':
    unittest.main()
