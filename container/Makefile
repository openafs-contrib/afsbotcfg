SUBDIRS := $(wildcard */.)

.PHONY: build
build:
	@for subdir in $(SUBDIRS); do \
		$(MAKE) -C $$subdir build; \
	done
