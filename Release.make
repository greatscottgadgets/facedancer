#
# This file is part of Facedancer.
# Maintainer quick actions for generating releases.
#


# By default, use the system's "python3" binary; but note that some distros now 
# correctly have 'python' as python3.
PYTHON  ?= python3

all: prepare_release
.PHONY: prepare_release

PROJECT = facedancer

ifndef VERSION
$(error This Makefile is for release maintainers; and requires VERSION to be defined for a release.)
endif

# Flags for creating build archives.
# These effectively tell the release tool how to modify git-archive output to create a complete build.
ARCHIVE_FLAGS = \
	--extra=VERSION $(HOST_PACKAGE_FLAGS) --prefix=$(PROJECT)-$(VERSION)/

#
# Prepares a Facedancer release based on the VERSION arguments. 
# Currently, we don't yet have a RELEASENOTE filel or anything like that.
#
prepare_release:
	@mkdir -p release-files/

	@echo Tagging release $(VERSION).
	@git tag -a v$(VERSION) $(TAG_FORCE) -m "release $(VERSION)"
	@echo "$(VERSION)" > VERSION

	@echo --- Creating our host-python distribution.
	@rm -rf host-packages
	@mkdir -p host-packages

	@#Build the host libraries.
	@$(PYTHON) setup.py sdist bdist_wheel -d host-packages

	@echo --- Preparing the release archives.
	$(eval HOST_PACKAGE_FLAGS := $(addprefix --extra=, $(wildcard host-packages/*)))
	@git-archive-all $(ARCHIVE_FLAGS) release-files/$(PROJECT)-$(VERSION).tar.xz
	@git-archive-all $(ARCHIVE_FLAGS) release-files/$(PROJECT)-$(VERSION).zip

	@echo
	@echo Archives seem to be ready in ./release-files.
	@echo If everything seems okay, you probably should push the relevant tag:
	@echo "    git push origin v$(VERSION)"
	@echo
	@echo And push the relevant packages to Pypi:
	@echo "    python3 setup.py dsit bdist_wheel register upload"
