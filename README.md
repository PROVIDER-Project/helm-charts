# PROVIDER Helm charts

A shared chart for self-contained Ontop/DuckDB endpoint images. Each dataset
uses its own Helm release and values file; database builds stay in the dataset
repositories.

* For me its not yet clear whether to use one repo for all charts or split this up into different repos. Right now the naming suggests a central repo for all PROVIDER helm charts.
* Main use cases so far are the sparql/ontop services, such as [sparql-tiva-ontop](https://github.com/PROVIDER-Project/sparql-tiva-ontop) and [sparql-faostat-ontop](https://github.com/PROVIDER-Project/sparql-tiva-ontop). So far I used Flux CD to reconcile a k8s cluster based on the plain yaml files, but perhaps it gets a bit nicer with helm in between - so consider this is an ongoing experiment for what's the best way to manage those services.

## Install

Requires Kubernetes 1.25+ and Helm 3.12+ or 4. From this repository:

```sh
helm upgrade --install faostat ./charts/ontop -f examples/faostat.yaml \
  --namespace provider --create-namespace --wait --timeout 5m
helm test faostat --namespace provider --logs
```

Use `baci` / `examples/baci.yaml` or `tiva` / `examples/tiva.yaml` for the other
endpoints. The examples select these image repositories with tag `0.0.1`:

| Dataset | Endpoint image repository |
| --- | --- |
| FAOSTAT | `ghcr.io/provider-project/sparql-faostat-ontop` |
| BACI (2024) | `ghcr.io/provider-project/sparql-baci-ontop` |
| TiVA (FDVA 2022) | `ghcr.io/provider-project/sparql-tiva-ontop` |

Push the selected image first and ensure cluster nodes can pull it. Private
images need a Kubernetes registry Secret referenced by `imagePullSecrets`.
To build/publish an image, use `make build` / `make publish` in that dataset's
`endpoint/` folder. For Kind, a locally built image can instead be loaded using
`kind load docker-image IMAGE --name CLUSTER`.

Ingress is disabled by default. To try the installed endpoint locally:

```sh
kubectl -n provider port-forward service/faostat-ontop 8081:80
# SPARQL: http://localhost:8081/sparql
```

## Configure

Override values per deployment, for example:

```sh
helm upgrade --install faostat ./charts/ontop -f examples/faostat.yaml \
  --namespace provider --set image.tag=0.0.2
```

Use `image.digest` to pin an image exactly. Configure `ingress`, `resources`,
`tmp.sizeLimit` and placement for the target cluster; large datasets such as
TiVA need query-specific memory and scratch-space sizing. See the
[chart README](charts/ontop/README.md) for the runtime contract and values.

The chart consumes only the endpoint image. It creates a Deployment, Service,
optional Ingress and test Pod; no Maven resolution, database loading or PVC is
involved. Chart, endpoint and database versions are independent. A new dataset
image does not require a new chart release.

## Validate and package

Requires Helm, Python 3 and PyYAML (`requirements-dev.txt`). Set `HELM_BIN` if
Helm is outside PATH.

```sh
./scripts/check.sh
./scripts/package.sh
```

Validation lints all dataset examples and checks rendered manifests without a
cluster. Packaging writes `dist/ontop-0.1.2.tgz`.

## Publish the chart

For OCI distribution through GHCR (authenticate with package write access):

```sh
helm registry login ghcr.io --username YOUR_GITHUB_USER
./scripts/package.sh
helm push dist/ontop-0.1.2.tgz oci://ghcr.io/provider-project/charts
```

After publishing, replace `./charts/ontop` in install commands with
`oci://ghcr.io/provider-project/charts/ontop --version 0.1.2`.
Chart registry login and Kubernetes image pull credentials are separate.
Keep chart versions immutable; configure package visibility for intended users.

## Licence

Original project material is licensed under [Apache-2.0](LICENSE).
See [licensing notes](LICENSING.md) for third-party terms and the declaration
that information about those terms was derived with AI assistance.
