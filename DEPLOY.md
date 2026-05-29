# Despliegue API — api.autolavados.cl

El panel admin llama a `https://api.autolavados.cl/api/...` (login: `POST /api/auth/login`).

## Por qué da 404 hoy

En producción **aún corre otro API** (legacy: `/api/authentications/login`, facturas, etc.).
Ese servicio **no** expone `/api/auth/login` del panel CarWash.

Hay que **reemplazar** ese proceso por el backend de esta carpeta (`autolavados.cl/backend`).

## Comprobar después del deploy

```bash
curl https://api.autolavados.cl/api/health
# → {"status":"ok"}

curl -X POST https://api.autolavados.cl/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@autolavados.cl","password":"TU_CLAVE"}'
# → 200 con access_token (o 401 si credenciales incorrectas, no 404)
```

Si `/api/health` sigue en 404, nginx sigue apuntando al API viejo.

## Requisitos en el servidor

- Python 3.12+ o Docker
- MySQL con base `autolavados` y migraciones aplicadas (`migrations/*.sql`)
- Nginx + certificado TLS para `api.autolavados.cl`
- DNS `api.autolavados.cl` → IP del servidor

## Opción A — Docker (recomendada)

En el servidor:

```bash
git clone <repo> /opt/autolavados-api
cd /opt/autolavados-api/backend
cp .env.production.example .env
# Editar .env: DATABASE_URL, JWT_SECRET_KEY, DEFAULT_ADMIN_PASSWORD

docker compose up -d --build
```

Nginx debe hacer proxy a `127.0.0.1:8000` (ver `deploy/nginx-api.autolavados.cl.conf`).

## Opción B — systemd + venv

```bash
sudo mkdir -p /opt/autolavados-api
sudo rsync -av --exclude .git ./backend/ /opt/autolavados-api/
cd /opt/autolavados-api
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.production.example .env
# editar .env

sudo cp deploy/autolavados-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now autolavados-api
```

## Nginx

1. Detener el servicio del API legacy (systemd/docker que escucha en el puerto actual).
2. Copiar `deploy/nginx-api.autolavados.cl.conf` a `/etc/nginx/sites-available/`.
3. `sudo ln -sf .../sites-available/api.autolavados.cl .../sites-enabled/`
4. `sudo nginx -t && sudo systemctl reload nginx`
5. `sudo certbot --nginx -d api.autolavados.cl` si falta HTTPS.

## Desarrollo local (mientras no esté en producción)

Admin frontend (`.env.local`):

```env
VITE_API_URL=http://127.0.0.1:8050
```

Backend:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp .env.example .env
python main.py
```

Login local: `http://127.0.0.1:8050/api/auth/login`

## Firebase admin (frontend)

Tras desplegar el API, rebuild del panel:

```bash
cd admin-frontend
# .env.production o build con VITE_API_URL=https://api.autolavados.cl
npm run deploy
```

`VITE_API_URL` solo necesita el host; el cliente agrega `/api` automáticamente.
