========================================
  Loan Radar - Windows Delivery Package
========================================

Quick start
-----------

1. Install and start Docker Desktop.
2. Double-click start.bat.
3. Wait for the health checks to finish.
4. The browser opens the Web UI automatically.

URLs
----

Web UI:       http://localhost
Backend API:  http://localhost:8001/docs
MediaCrawler: http://localhost:8080/docs
PostgreSQL:   localhost:5432

What start.bat does
-------------------

- Checks Docker and Docker Compose.
- Starts PostgreSQL, MediaCrawler, backend, and frontend with Docker Compose.
- Builds images automatically if they do not exist.
- Waits for backend and MediaCrawler health endpoints.
- Opens the Web UI.

Common commands
---------------

Run these commands in this folder:

docker compose ps
docker compose logs -f
docker compose restart
docker compose down
start.bat --build
check-delivery.bat

Troubleshooting
---------------

Docker not found:
Install Docker Desktop from https://www.docker.com/products/docker-desktop

Docker is installed but not running:
Open Docker Desktop and wait until it is ready.

Port already in use:
Ports 80, 8001, 8080, and 5432 must be free. Stop the conflicting app or edit
docker-compose.yml before starting.

Service starts but page is unavailable:
Run "docker compose ps" and "docker compose logs --tail=120" in this folder.

First run cannot download base images:
The included Dockerfiles use DaoCloud's public mirror by default:
m.daocloud.io/docker.io/library/python
m.daocloud.io/docker.io/library/node
m.daocloud.io/docker.io/library/nginx

Python packages use Tsinghua PyPI mirror by default:
https://pypi.tuna.tsinghua.edu.cn/simple

Debian packages use Tsinghua Debian mirror by default:
https://mirrors.tuna.tsinghua.edu.cn/debian

To use Docker Hub directly, edit the Dockerfile build args back to:
python:3.11-slim, node:20-alpine, nginx:alpine.
