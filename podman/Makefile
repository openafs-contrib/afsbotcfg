SUBDIRS := $(wildcard */*)

.PHONY: images
images:
	@for subdir in $(SUBDIRS); do \
		$(MAKE) -C $$subdir image; \
	done
