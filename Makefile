VALID_PROFILES := base bgp-attributes monitor-connectivity pingcheck interface-tracking

define check_profile
	@if [ -z "$(PROFILE)" ]; then \
		echo "Error: PROFILE is required. Valid: $(VALID_PROFILES)"; \
		exit 1; \
	fi
	@if ! echo "$(VALID_PROFILES)" | grep -qw "$(PROFILE)"; then \
		echo "Error: invalid profile '$(PROFILE)'. Valid: $(VALID_PROFILES)"; \
		exit 1; \
	fi
endef

.PHONY: build topology deploy switch validate destroy lab clean

build:
	$(call check_profile)
	python3 scripts/generate_configs.py --profile $(PROFILE)

topology:
	$(call check_profile)
	python3 scripts/generate_topology.py --profile $(PROFILE)

deploy:
	$(call check_profile)
	python3 scripts/deploy.py --profile $(PROFILE)

switch:
	$(call check_profile)
	python3 scripts/deploy.py --profile $(PROFILE) --switch-only

validate:
	$(call check_profile)
	python3 scripts/validate.py --profile $(PROFILE)

destroy:
	containerlab destroy --topo topology.yml --cleanup

lab:
	$(call check_profile)
	$(MAKE) deploy PROFILE=$(PROFILE)
	$(MAKE) validate PROFILE=$(PROFILE)

clean:
	rm -rf intended/configs/ topology.yml
