# new_bot
telegram bot to accumulate posts from channels you subscribe

## Minikube (Postgres + db_api + Redis)
1. Start minikube:
```bash
minikube start --cpus=4 --memory=8192 --driver=docker
```

2. Build db_api image inside minikube:
```bash
eval $(minikube -p minikube docker-env)
docker build -t db-api:latest ./db_api
```

3. Install Postgres:
```bash
helm install postgres ./charts/postgres
```

4. Install Redis:
```bash
helm install redis ./charts/redis
```

5. Install db_api (use a different release name than postgres):
```bash
helm install db-api ./charts/db_api
```

## Userbot Env
Run userbot with:
```bash
export API_BASE_URL=http://localhost:8080
export REDIS_URL=redis://localhost:6379/0
export DELIVERY_WORKERS=1
export DELIVERY_MIN_INTERVAL_SEC=0.35
export LLM_API_KEY=<your_key>
export LLM_MODEL=gpt-4o-mini
# optional:
# export LLM_API_BASE=https://api.openai.com/v1
```

## Automation Scripts
Deploy all Kubernetes components (minikube + build + helm):
```bash
./scripts/deploy_k8s.sh
```

Start local port-forwards:
```bash
./scripts/dev_port_forward.sh
```

Run userbot with sane defaults:
```bash
./scripts/run_userbot.sh
```

One command for full local startup:
```bash
./scripts/up.sh
```

Optional flags:
```bash
DEPLOY=0 ./scripts/up.sh
PORT_FORWARD=0 ./scripts/up.sh
```

### Server mode (future)
If you already have Kubernetes cluster and image in registry:
```bash
USE_MINIKUBE=0 BUILD_DB_API_IMAGE=0 ./scripts/deploy_k8s.sh
```
