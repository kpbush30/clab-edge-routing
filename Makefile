TOPO ?= clab/topology.clab.yml

.DEFAULT_GOAL := help

.PHONY: help deploy status recreate destroy clean

help:
	@echo "Edge Routing Resiliency Lab"
	@echo ""
	@echo "  make deploy     Deploy the lab from its startup configs"
	@echo "  make status     Show running nodes, mgmt IPs, and ports"
	@echo "  make recreate   Destroy and redeploy from scratch (fresh boot)"
	@echo "  make destroy    Tear down the lab, keep generated lab files"
	@echo "  make clean      Tear down the lab and remove generated lab files"
	@echo ""
	@echo "If your containerlab/docker setup needs elevated privileges, prefix"
	@echo "any target with sudo, e.g.: sudo make deploy"

deploy:
	sudo containerlab deploy --debug -t $(TOPO) --max-workers 10 --timeout 5m --reconfigure

status:
	containerlab inspect -t $(TOPO)

recreate:
	containerlab destroy -t $(TOPO) --cleanup
	containerlab deploy -t $(TOPO)

destroy:
	containerlab destroy -t $(TOPO)

clean:
	containerlab destroy -t $(TOPO) --cleanup
