UV := uv
VERSION ?= 1.0.0

DIST_DIR := dist
BUILD_DIR := build

UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)
ARCHIVE_NAME := PyeClaw-$(UNAME_S)-$(UNAME_M)

.DEFAULT_GOAL := help

.PHONY: help install run build clean publish lint set-version

# show available targets
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@echo "  install       install python dependencies"
	@echo "  run           run the application in development mode"
	@echo "  build         build distributable with pyinstaller"
	@echo "  publish       build and create distributable archive"
	@echo "  clean         remove all build artifacts"
	@echo "  lint          run linting checks"
	@echo "  set-version   set app version (VERSION=x.y.z)"

# install python dependencies
install:
	$(UV) sync

# run the application in development mode
run:
	$(UV) run python -m pyeclaw

# build the distributable application with pyinstaller
build: install
	$(UV) run pyinstaller pyeclaw.spec --noconfirm --clean

# remove all build artifacts
clean:
	rm -rf $(BUILD_DIR) $(DIST_DIR) *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

# create a distributable archive from the build output
publish: build
ifeq ($(UNAME_S),Darwin)
	cd $(DIST_DIR) && tar -czf $(ARCHIVE_NAME).tar.gz PyeClaw.app
else
	cd $(DIST_DIR) && tar -czf $(ARCHIVE_NAME).tar.gz PyeClaw
endif
	@echo "archive created: $(DIST_DIR)/$(ARCHIVE_NAME).tar.gz"

# run linting checks
lint:
	$(UV) run ruff check pyeclaw/
	$(UV) run ruff format --check pyeclaw/

# set app version in all source files (usage: make set-version VERSION=1.2.3)
set-version:
	@python3 scripts/set_version.py $(VERSION)
