# PROVIDER Helm charts

**Work in progress**

* For me its not yet clear whether to use one repo for all charts or split this up into different repos. Right now the naming suggests a central repo for PROVIDER helm charts.
* Main use cases so far are the sparql/ontop services, such as [sparql-tiva-ontop](https://github.com/PROVIDER-Project/sparql-tiva-ontop) and [sparql-faostat-ontop](https://github.com/PROVIDER-Project/sparql-tiva-ontop). So far I used Flux CD to reconcile a k8s cluster based on the plain yaml files, but perhaps it gets a bit nicer with helm in between - so consider this is an ongoing experiment for what's the best way to manage those services.

## Synopsis

Shared Kubernetes charts for PROVIDER endpoints. This directory is ready to
be managed as an independent Git repository; this setup made no Git changes.
The proposed source URL is `https://github.com/PROVIDER-Project/helm-charts`;
update chart metadata if the eventual repository uses another location.

- `charts/ontop/`: application chart for self-contained, read-only Ontop/DuckDB images.
- `examples/faostat.yaml`: values for the existing local FAOSTAT image.
- `examples/tiva.yaml`: template for a future self-contained TiVA image.
- `tests/`: rendering contracts, independent of the dataset build repositories.
- `scripts/check.sh`, `scripts/package.sh`: validation and local packaging.

## Install from source

Run from this directory. Build the FAOSTAT image in its sibling repository:

```sh
(cd ../sparql-faostat-ontop && docker compose build)
# For Kind (otherwise publish the image to a registry accessible to your nodes):
kind load docker-image provider/sparql-faostat-ontop:0.0.1 --name YOUR_CLUSTER
helm upgrade --install faostat ./charts/ontop -f examples/faostat.yaml \
  --namespace provider --create-namespace --wait --timeout 5m
helm test faostat --namespace provider --logs
```

For a remote registry, override `image.repository` and `image.tag`, or pin
`image.digest`. Supply registry credentials with `imagePullSecrets` if needed.
No image is implicitly selected: both the repository and a tag or digest are
required. Ingress is disabled in the examples; configure hostname, controller
class and TLS for the target cluster before enabling it.

TiVA currently needs its data, JDBC driver and configuration mounted by Compose.
Its example is a template with explicit placeholder image coordinates, not a
ready-to-install endpoint. First build an image containing these files and
meeting the [runtime contract](charts/ontop/README.md).

## Validate and package

Requires Helm 3.12+ or Helm 4, Python 3 and PyYAML (`requirements-dev.txt`).
`HELM_BIN` can select a Helm executable outside PATH.

```sh
./scripts/check.sh
./scripts/package.sh
```

The package is written to `dist/ontop-0.1.0.tgz`. Render tests require no cluster.
The check script fails when its dependencies are missing rather than silently
skipping validation. Packaging validates first.

## Publish to an OCI registry

Source hosting and chart distribution are independent. After creating the Git
repository, publish packaged charts to an OCI registry such as GHCR. These are
proposed coordinates; neither this registry package nor the Git repository is
assumed to exist. Authenticate using an account/token with package write access:

```sh
helm registry login ghcr.io --username YOUR_GITHUB_USER
./scripts/package.sh
helm push dist/ontop-0.1.0.tgz oci://ghcr.io/provider-project/charts
```

Helm appends the chart name and version. Consumers can then install it with:

```sh
helm upgrade --install faostat oci://ghcr.io/provider-project/charts/ontop \
  --version 0.1.0 -f examples/faostat.yaml \
  --namespace provider --create-namespace --wait --timeout 5m
```

Make the registry package public if anonymous installation is intended; private
charts require `helm registry login` for consumers as well. Endpoint image pull
credentials are separate Kubernetes Secrets. See the official
[Helm OCI documentation](https://helm.sh/docs/topics/registries/).

Increment `charts/ontop/Chart.yaml` version for chart changes and publish a new
immutable package version. The chart's `appVersion` documents its reference
Ontop runtime; image tags/digests independently identify each dataset release.
A new data image does not require publishing a new chart. Keep environment
values (image pins, hostnames, TLS, resources) in the deployment/GitOps repository.

CI can run `scripts/check.sh` on changes and `scripts/package.sh` plus `helm push`
on release tags once the source host and registry credentials are configured.
No workflow tied to unpublished registry credentials is installed here.
