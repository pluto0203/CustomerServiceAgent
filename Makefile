SHELL := /bin/bash

.PHONY: up down logs build test

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f api worker

build:
	docker compose build

test:
	cd backend && pytest -q
