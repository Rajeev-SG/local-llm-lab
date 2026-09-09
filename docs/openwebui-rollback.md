# Open WebUI Rollback

Rollback changes the container image only. It never removes `open-webui-data`.

```bash
./scripts/rollback-openwebui.sh ghcr.io/open-webui/open-webui:v0.8.10
./scripts/doctor.sh
```

Use the last known-good version tag or full image digest from the deployment record. Stop the service first with `./scripts/stop-openwebui.sh` only when diagnosing a running-container issue. If the named volume is suspected, stop and preserve it for backup or inspection; never run `docker volume rm` or `docker compose down -v` as a rollback step.
