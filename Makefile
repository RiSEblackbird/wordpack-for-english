.PHONY: deploy-firestore-indexes
.PHONY: deploy-cloud-run
.PHONY: release-cloud-run

CLOUD_RUN_SCRIPT := ./scripts/deploy_cloud_run.sh
DEPLOY_CLOUD_RUN_ARGS = $(if $(PROJECT_ID),--project-id $(PROJECT_ID),) \
        $(if $(REGION),--region $(REGION),) \
        $(if $(SERVICE),--service $(SERVICE),) \
        $(if $(ARTIFACT_REPO),--artifact-repo $(ARTIFACT_REPO),) \
        $(if $(IMAGE_TAG),--image-tag $(IMAGE_TAG),) \
        $(if $(BUILD_ARG),--build-arg $(BUILD_ARG),) \
        $(if $(MACHINE_TYPE),--machine-type $(MACHINE_TYPE),) \
        $(if $(BUILD_TIMEOUT),--timeout $(BUILD_TIMEOUT),) \
        $(if $(GENERATE_SECRET),--generate-secret,) \
        $(if $(SECRET_LENGTH),--secret-length $(SECRET_LENGTH),) \
        $(if $(DRY_RUN),--dry-run,) \
        $(if $(ENV_FILE),--env-file $(ENV_FILE),)

SKIP_FIRESTORE_INDEX_SYNC ?= false

# 使用例:
#   make deploy-firestore-indexes PROJECT_ID=my-gcp-project
#   make deploy-firestore-indexes PROJECT_ID=my-firebase-project TOOL=firebase

deploy-firestore-indexes:
	./scripts/deploy_firestore_indexes.sh $(if $(PROJECT_ID),--project $(PROJECT_ID),) $(if $(TOOL),--tool $(TOOL),)

deploy-cloud-run:
	$(CLOUD_RUN_SCRIPT) $(DEPLOY_CLOUD_RUN_ARGS)

release-cloud-run: ENV_FILE ?= .env.deploy
# release-cloud-run: Firestore インデックス同期 → Cloud Run dry-run → 本番デプロイを一括で行い、
# `.env.deploy` などの env ファイル存在チェックと dry-run 成功を必須条件にしています。
release-cloud-run:
	@set -euo pipefail; \
	# 一連のリリース処理で必須パラメータや前提ファイルの欠落を早期に検出する。
	PROJECT_ID_VALUE="$(PROJECT_ID)"; \
	REGION_VALUE="$(REGION)"; \
	ENV_FILE_PATH="$(ENV_FILE)"; \
	SKIP_INDEX_SYNC="$(SKIP_FIRESTORE_INDEX_SYNC)"; \
	if [ -z "$$PROJECT_ID_VALUE" ]; then \
	echo "[release-cloud-run] PROJECT_ID is required (pass PROJECT_ID= or export the variable)" >&2; \
	exit 1; \
	fi; \
	if [ -z "$$REGION_VALUE" ]; then \
	echo "[release-cloud-run] REGION is required (pass REGION= or export the variable)" >&2; \
	exit 1; \
	fi; \
	if [ -z "$$ENV_FILE_PATH" ]; then \
	echo "[release-cloud-run] ENV_FILE is required; default .env.deploy was not resolved" >&2; \
	exit 1; \
	fi; \
	if [ ! -f "$$ENV_FILE_PATH" ]; then \
	echo "[release-cloud-run] Env file not found: $$ENV_FILE_PATH" >&2; \
	echo "Please prepare the file (cp env.deploy.example $$ENV_FILE_PATH) before releasing." >&2; \
	exit 1; \
	fi; \
	if [ "$$SKIP_INDEX_SYNC" != "true" ]; then \
	echo "[release-cloud-run] Syncing Firestore indexes before deployment"; \
	$(MAKE) --no-print-directory deploy-firestore-indexes PROJECT_ID="$$PROJECT_ID_VALUE" $(if $(TOOL),TOOL=$(TOOL),); \
	else \
	echo "[release-cloud-run] Skipping Firestore index sync because SKIP_FIRESTORE_INDEX_SYNC=true"; \
	fi; \
	echo "[release-cloud-run] Validating Cloud Run configuration via dry-run"; \
	$(CLOUD_RUN_SCRIPT) $(DEPLOY_CLOUD_RUN_ARGS) --dry-run; \
	echo "[release-cloud-run] Dry-run succeeded. Deploying to Cloud Run"; \
	$(CLOUD_RUN_SCRIPT) $(DEPLOY_CLOUD_RUN_ARGS)
