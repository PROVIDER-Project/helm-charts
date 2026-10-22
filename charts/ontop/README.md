# Ontop endpoint chart

An application chart for a self-contained Ontop image containing its DuckDB
database, JDBC driver, mappings, properties, lenses and constraints. It creates
a Deployment, Service, optional Ingress and Helm connection-test Pod. Every
replica serves its own read-only database snapshot from the image.

Installation, validation, packaging and OCI publication instructions are in the
[repository README](../../README.md). Kubernetes 1.25+ and Helm 3.12+/4 are required.

## Image runtime contract

The only application artifact consumed by the chart is the endpoint image.
There is no Maven download, data loader, PVC or mapping ConfigMap. The image must:

- Contain all data/configuration and start the endpoint without host bind mounts.
- Listen on port 8080 and serve SPARQL at `/sparql`.
- Run with the selected security context (default UID/GID 999, matching Ontop 5.5.0).
- Work with a read-only root filesystem and writable `/tmp`.
- Include `wget` for the Helm connection test.

Configure DuckDB spill files under `/tmp`, for example with the JDBC property
`jdbc.property.temp_directory=/tmp/duckdb`. Native JDBC extraction also needs
writable temporary storage. The database itself remains read-only in the image.
The chart does not provision mutable database storage.

These are the assumptions shared by compatible FAOSTAT, TiVA and future images.
Kubernetes runtime settings (resources, placement, registry credentials, exposure)
remain deployment configuration. An Ingress controller and TLS Secret must exist
externally when Ingress is enabled.

## Values

All settings have comments in [values.yaml](values.yaml); the JSON schema rejects
invalid inputs. Defaults deliberately leave image repository and tag empty.
Pass an example values file or set the image explicitly, including during linting.

| Setting | Purpose |
| --- | --- |
| `image.repository`, `image.tag` | Required endpoint image coordinates |
| `image.digest` | Optional SHA-256 digest, takes precedence over the tag |
| `image.pullPolicy`, `imagePullSecrets` | Pull policy and namespace registry Secrets |
| `replicaCount` | Independent read-only replicas, default 1 |
| `service.type`, `service.port` | Defaults ClusterIP and port 80, targeting container port 8080 |
| `ingress.*` | Hostnames, paths, controller class, annotations and TLS; disabled by default |
| `env` | String-valued Ontop environment overrides |
| `resources` | CPU, memory and ephemeral-storage requests/limits |
| `tmp.sizeLimit` | Disk-backed writable `/tmp`, default 1Gi |
| `startupProbe`, `readinessProbe`, `livenessProbe` | Kubernetes health checks |
| `podSecurityContext`, `securityContext` | Non-root execution and container restrictions |
| `strategy` | RollingUpdate by default; Recreate also supported |
| `nodeSelector`, `tolerations`, `affinity` | Pod placement |

Readiness runs `ASK {}` over HTTP; startup/liveness use TCP. Kubernetes does not
use the Docker image's `HEALTHCHECK`. `helm test` queries the Service using the
selected endpoint image; the successful test Pod is removed.

Default JVM heap is 128–512 MiB, with pod memory request/limit 512Mi/2Gi. DuckDB
allocates native memory beyond the JVM heap. Measure representative queries
before selecting production memory and scratch space. Ephemeral-storage
request/limit are 256Mi/2Gi; logs also consume ephemeral storage.

## Updates and rollback

Use immutable image tags or digests. Rolling updates can briefly serve both old
and new data revisions; `strategy.type: Recreate` avoids concurrent revisions
with downtime. For coordinated changes use separate releases and switch traffic.

```sh
helm history faostat --namespace provider
helm rollback faostat PREVIOUS_REVISION --namespace provider --wait
helm uninstall faostat --namespace provider
```

Rollback requires the referenced image to remain available. Uninstallation
leaves no database PVC to clean up. Each dataset uses its own Helm release and
values; chart version, Ontop appVersion and endpoint image version are independent.

## Validation history

Before extraction from the FAOSTAT repository, this deployment was verified with
Helm 4.3.1 and temporary Kind 0.33.0 / Kubernetes 1.37.0: installation, Service
queries, Helm test, scaling to two replicas and rollback passed under non-root
execution with a read-only root/database and writable `/tmp`. Ingress/TLS and
Recreate manifests passed server dry-run; external Ingress/TLS routing was not
tested. The standalone repository keeps and extends the rendering contracts.
