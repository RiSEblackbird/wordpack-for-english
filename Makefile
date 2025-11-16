.PHONY: deploy-firestore-indexes

# 使用例:
#   make deploy-firestore-indexes PROJECT_ID=my-gcp-project
#   make deploy-firestore-indexes PROJECT_ID=my-firebase-project TOOL=firebase

deploy-firestore-indexes:
	./scripts/deploy_firestore_indexes.sh $(if $(PROJECT_ID),--project $(PROJECT_ID),) $(if $(TOOL),--tool $(TOOL),)
