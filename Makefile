SHELL := /bin/sh

UV ?= uv
UV_DEFAULT_INDEX ?= https://pypi.org/simple
export UV_DEFAULT_INDEX
PNPM ?= pnpm
API_DIR := apps/api
WEB_PACKAGE := @beatprints/web

.DEFAULT_GOAL := help

.PHONY: help setup dev dev\:api dev\:web sync\:api install\:web start\:api test test\:api lint lint\:api format\:api lock lock\:api lock\:web build build\:api build\:web docker\:up docker\:down docker\:logs

help: ## 显示可用命令
	@printf '%s\n' \
		'  setup         安装 API 与 Web 依赖' \
		'  dev           同时启动 API 和 Web' \
		'  dev:api       只启动 FastAPI 热更新服务' \
		'  dev:web       只启动 Web 开发服务' \
		'  sync:api      使用 uv 同步 API 依赖' \
		'  install:web   使用 pnpm 安装 workspace 依赖' \
		'  start:api     使用生产入口启动 API' \
		'  test:api      运行 API 测试' \
		'  lint:api      检查 Python 格式' \
		'  format:api    格式化 Python 代码' \
		'  lock:api      更新 uv.lock' \
		'  lock:web      更新 pnpm-lock.yaml' \
		'  build:api     构建 Python 包' \
		'  build:web     构建 Web 应用' \
		'  docker:up     构建并启动生产容器' \
		'  docker:down   停止生产容器' \
		'  docker:logs   跟踪 API 容器日志'

setup: sync\:api install\:web ## 安装全部依赖

sync\:api: ## 使用 uv 同步 API 依赖
	cd $(API_DIR) && UV_DEFAULT_INDEX=$(UV_DEFAULT_INDEX) $(UV) sync --locked

install\:web: ## 安装 pnpm workspace 依赖
	$(PNPM) install --frozen-lockfile

dev: ## 同时启动 API 和 Web；Web 未初始化时只运行 API
	@if [ -f "apps/web/package.json" ]; then \
		$(PNPM) exec concurrently --kill-others-on-fail \
			--names api,web --prefix-colors blue,magenta \
			"$(MAKE) dev:api" "$(MAKE) dev:web"; \
	else \
		$(MAKE) dev:api; \
	fi

dev\:api: ## 只启动 FastAPI 热更新服务
	@if [ -f ".env" ]; then \
		cd $(API_DIR) && $(UV) run uvicorn beatprints_api.main:app --reload --env-file ../../.env; \
	else \
		cd $(API_DIR) && $(UV) run uvicorn beatprints_api.main:app --reload; \
	fi

dev\:web: ## 只启动 Web 开发服务
	$(PNPM) --filter $(WEB_PACKAGE) --if-present dev

start\:api: ## 使用生产入口启动 API
	cd $(API_DIR) && $(UV) run beatprints-api

test: test\:api ## 运行全部测试

test\:api: ## 运行 API 测试
	cd $(API_DIR) && $(UV) run pytest

lint: lint\:api ## 运行全部静态检查

lint\:api: ## 检查 Python 格式
	cd $(API_DIR) && $(UV) run black --check src tests

format\:api: ## 格式化 Python 代码
	cd $(API_DIR) && $(UV) run black src tests

lock: lock\:api lock\:web ## 更新全部锁文件

lock\:api: ## 更新 uv.lock
	cd $(API_DIR) && UV_DEFAULT_INDEX=$(UV_DEFAULT_INDEX) $(UV) lock

lock\:web: ## 更新 pnpm-lock.yaml
	$(PNPM) install --lockfile-only

build: build\:api build\:web ## 构建全部应用

build\:api: ## 构建 Python 包
	cd $(API_DIR) && $(UV) build

build\:web: ## 构建 Web 应用
	$(PNPM) --filter $(WEB_PACKAGE) --if-present build

docker\:up: ## 构建并启动生产容器
	docker compose up -d --build

docker\:down: ## 停止生产容器
	docker compose down

docker\:logs: ## 跟踪 API 容器日志
	docker compose logs -f beatprints-api
