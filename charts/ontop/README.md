# Ontop endpoint chart

Deploy a self-contained Ontop/DuckDB image as a Deployment, Service, optional
Ingress and Helm connection-test Pod. Each replica serves its own read-only
snapshot. See [installation and publishing](../../README.md).

## Image contract

FAOSTAT, BACI and TiVA endpoint images contain their database, JDBC driver,
mappings and configuration. Compatible images must:

- Serve `/sparql` on container port 8080.
- Run without host data/configuration mounts.
- Support the selected non-root user (default UID/GID 999, Ontop 5.5.0).
- Work with a read-only root filesystem and writable `/tmp`.
- Include `wget` for the Helm connection test.

DuckDB opens the database read-only and spills under `/tmp/duckdb`. JDBC native
library extraction also uses temporary storage. The chart provides `/tmp` as
an `emptyDir`; it does not provision database storage or run build tools.

## Values

Use a dataset file from `examples/` or supply an explicit image. The default
[values.yaml](values.yaml) leaves image repository and tag empty; the schema
requires a repository and either a tag or digest.

| Setting | Purpose |
| --- | --- |
| `image.repository`, `image.tag` | Endpoint image coordinates |
| `image.digest` | SHA-256 digest; takes precedence over the tag |
| `image.pullPolicy`, `imagePullSecrets` | Pull policy and registry Secrets |
| `replicaCount` | Independent read-only replicas; default 1 |
| `service.*` | ClusterIP port 80, targeting container port 8080 by default |
| `ingress.*` | Controller class, hostnames, paths and TLS; disabled by default |
| `env` | String-valued Ontop environment overrides |
| `resources`, `tmp.sizeLimit` | CPU, memory and ephemeral storage |
| `startupProbe`, `readinessProbe`, `livenessProbe` | Health checks |
| `podSecurityContext`, `securityContext` | Runtime permissions |
| `strategy` | `RollingUpdate` or `Recreate` |
| `nodeSelector`, `tolerations`, `affinity` | Placement |

Readiness sends `ASK {}`; startup and liveness use TCP. `helm test` queries the
Service with the selected endpoint image. Kubernetes does not use the image's
Docker healthcheck.

Defaults allow a 128–512 MiB JVM heap, a 2Gi pod memory limit and 1Gi `/tmp`.
DuckDB allocates additional native memory. These are starting values, not
full-dataset sizing guarantees; measure representative queries, especially for
TiVA. Supply the Ingress controller and TLS Secrets separately.

## Updates and rollback

Use immutable image tags or digests. Rolling updates can briefly serve two data
revisions; `strategy.type: Recreate` avoids overlap with downtime.

```sh
helm history faostat --namespace provider
helm rollback faostat PREVIOUS_REVISION --namespace provider --wait
helm uninstall faostat --namespace provider
```

Rollback requires the previous image to remain available. Uninstall leaves no
database PVC. Each dataset has its own release; image and chart versions remain
independent.
