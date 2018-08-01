
BUILDBOT=$(HOME)/buildbot13/venv/bin/buildbot
MASTER=$(HOME)/buildbot13/master

help:
	@echo "make <target> [<target>...]"
	@echo "targets:"
	@echo "  start     start the buildmaster"
	@echo "  stop      stop the buildmaster"
	@echo "  restart   restart the buildmaster"
	@echo "  check     check the master.cfg file"
	@echo "  reload    reload the running buildmaster"

start:
	$(BUILDBOT) start $(MASTER)

stop:
	$(BUILDBOT) stop $(MASTER)

restart:
	$(BUILDBOT) restart $(MASTER)

checkconfig:
	$(BUILDBOT) checkconfig $(MASTER)

reconfig:
	$(BUILDBOT) reconfig $(MASTER)

# Aliases
check: checkconfig
reload: reconfig
