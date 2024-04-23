SHELL=/bin/bash
.PHONY: delete_ips
N_ROUTERS:=32

KCTL:=minikube kubectl --
NS:=datahangar-stack

check: _add_ips _start_nfacctd _run_routers _check_outputs

_start_nfacctd:
	$(KCTL) create namespace $(NS) || true
	$(KCTL) -n $(NS) create configmap nfacctd-mock-binary --from-file=nfacctd_mock.py
	$(KCTL) -n $(NS) apply -f nfacctd-mock.yaml
	$(KCTL) -n $(NS) apply -f 03-service.yaml
_add_ips:
	@for (( i=1; i<=$(N_ROUTERS); i++ )); do sudo ip addr add 10.0.$$i.1/32 dev lo; done
_run_routers:
	while [[ "$$IP_LB_SVC" == "" ]]; do \
		IP_LB_SVC=`$(KCTL) -n $(NS) get svc flowlogs-ingestor-internal -o jsonpath="{.spec.clusterIP}"`; \
	done; \
	for (( i=1; i<=$(N_ROUTERS); i++ )); do \
		(./router_mock.py $$IP_LB_SVC 10.0.$$i.1 &); \
	done

_check_outputs:
	echo "Checking outputs"

clean: _stop_routers _stop_nfacctd _delete_ips
_stop_routers:
	killall -9 router_mock.py || true
_stop_nfacctd:
	$(KCTL) delete namespace $(NS) || true
_delete_ips:
	@for (( i=1; i<=$(N_ROUTERS); i++ )); do sudo ip addr del 10.0.$$i.1/32 dev lo; done || true
