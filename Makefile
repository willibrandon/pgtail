# pgtail Makefile
# Cross-platform build targets for macOS, Linux, and Windows

VERSION := 0.1.0

# Detect Windows and add .exe extension
ifeq ($(OS),Windows_NT)
    BINARY := pgtail.exe
    RM := del /q
    RMDIR := rmdir /s /q
    RUN_PREFIX := .\
    MKDIR := mkdir
else
    BINARY := pgtail
    RM := rm -f
    RMDIR := rm -rf
    RUN_PREFIX := ./
    MKDIR := mkdir -p
endif
BUILD_DIR := build
CMD_DIR := ./cmd/pgtail

# Build flags
LDFLAGS := -ldflags "-s -w -X main.Version=$(VERSION)"

# Default target
.PHONY: all
all: build

# Build for current platform
.PHONY: build
build:
	go build $(LDFLAGS) -o $(BINARY) $(CMD_DIR)

# Run tests
.PHONY: test
test:
	go test -v ./...

# Run linter
.PHONY: lint
lint:
	golangci-lint run ./...

# Clean build artifacts
.PHONY: clean
clean:
	-$(RM) $(BINARY)
	-$(RMDIR) $(BUILD_DIR)

# Cross-compile for all platforms
.PHONY: release
release: clean build-darwin-arm64 build-darwin-amd64 build-linux-amd64 build-windows-amd64

# macOS ARM64 (Apple Silicon)
.PHONY: build-darwin-arm64
build-darwin-arm64:
	-@$(MKDIR) $(BUILD_DIR)
	GOOS=darwin GOARCH=arm64 go build $(LDFLAGS) -o $(BUILD_DIR)/pgtail-darwin-arm64 $(CMD_DIR)

# macOS AMD64 (Intel)
.PHONY: build-darwin-amd64
build-darwin-amd64:
	-@$(MKDIR) $(BUILD_DIR)
	GOOS=darwin GOARCH=amd64 go build $(LDFLAGS) -o $(BUILD_DIR)/pgtail-darwin-amd64 $(CMD_DIR)

# Linux AMD64
.PHONY: build-linux-amd64
build-linux-amd64:
	-@$(MKDIR) $(BUILD_DIR)
	GOOS=linux GOARCH=amd64 go build $(LDFLAGS) -o $(BUILD_DIR)/pgtail-linux-amd64 $(CMD_DIR)

# Windows AMD64
.PHONY: build-windows-amd64
build-windows-amd64:
	-@$(MKDIR) $(BUILD_DIR)
	GOOS=windows GOARCH=amd64 go build $(LDFLAGS) -o $(BUILD_DIR)/pgtail-windows-amd64.exe $(CMD_DIR)

# Install to GOBIN
.PHONY: install
install:
	go install $(LDFLAGS) $(CMD_DIR)

# Development helpers
.PHONY: run
run: build
	$(RUN_PREFIX)$(BINARY)

.PHONY: fmt
fmt:
	go fmt ./...

.PHONY: tidy
tidy:
	go mod tidy

# Show help
.PHONY: help
help:
	@echo "pgtail build targets:"
	@echo ""
	@echo "  make build    - Build for current platform"
	@echo "  make test     - Run tests"
	@echo "  make lint     - Run golangci-lint"
	@echo "  make clean    - Remove build artifacts"
	@echo "  make release  - Cross-compile for all platforms"
	@echo "  make install  - Install to GOBIN"
	@echo "  make run      - Build and run"
	@echo "  make fmt      - Format code"
	@echo "  make tidy     - Tidy go.mod"
	@echo ""
	@echo "Cross-compile targets:"
	@echo "  make build-darwin-arm64   - macOS ARM64"
	@echo "  make build-darwin-amd64   - macOS AMD64"
	@echo "  make build-linux-amd64    - Linux AMD64"
	@echo "  make build-windows-amd64  - Windows AMD64"
