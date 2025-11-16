.PHONY: deploy-firestore-indexes
.PHONY: deploy-cloud-run

# 使用例:
#   make deploy-firestore-indexes PROJECT_ID=my-gcp-project
#   make deploy-firestore-indexes PROJECT_ID=my-firebase-project TOOL=firebase

deploy-firestore-indexes:
	./scripts/deploy_firestore_indexes.sh $(if $(PROJECT_ID),--project $(PROJECT_ID),) $(if $(TOOL),--tool $(TOOL),)

deploy-cloud-run:
	./scripts/deploy_cloud_run.sh $(if $(PROJECT_ID),--project-id $(PROJECT_ID),) $(if $(REGION),--region $(REGION),) $(if $(SERVICE),--service $(SERVICE),) $(if $(ENV_FILE),--env-file $(ENV_FILE),)
