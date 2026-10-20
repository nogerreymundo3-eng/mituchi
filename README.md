# MI TUCHI 💗 — página romántica privada

Incluye:
- Inicio romántico con fondo de galaxia violeta/rosa.
- Acceso separado para administrador y novia.
- Panel de administración para editar nombres, historia y mensaje.
- Subida de múltiples fotos, leyendas y eliminación.
- SQLite para textos y metadatos; fotos en disco.
- Las fotos y páginas de recuerdos requieren sesión de novia o administrador.

## Ejecutar localmente en Termux

Desde la carpeta `mi-tuchi-web`:

```bash
pkg update
pkg install python -y
python -m pip install -r requirements.txt
export SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"
export ADMIN_PASSWORD='pon-aqui-una-clave-de-admin-larga'
export PARTNER_PASSWORD='pon-aqui-la-clave-que-le-daras-a-tu-novia'
export OWNER_NAME='mi renegón'
export PARTNER_NAME='Alejandra'
python app.py
```

Abre `http://localhost:8000`.
No compartas las contraseñas ni publiques un archivo `.env`.

## Publicar para que ella entre desde su teléfono

El servidor local de Termux NO crea un enlace público. Debes desplegar esta aplicación en un hosting que soporte Python/Flask, HTTPS, variables de entorno y almacenamiento persistente. En la configuración del hosting añade:

- `SECRET_KEY`: valor aleatorio largo y privado.
- `ADMIN_PASSWORD`: contraseña exclusiva del administrador.
- `PARTNER_PASSWORD`: contraseña para tu novia.
- `OWNER_NAME`: `mi renegón`
- `PARTNER_NAME`: `Alejandra`
- `DATA_DIR`: ruta de un disco/volumen persistente, por ejemplo `/var/data`
- `UPLOAD_DIR`: `/var/data/uploads`
- `DB_PATH`: `/var/data/mi_tuchi.sqlite3`

Configura un disco persistente en esa ruta. Si el hosting usa almacenamiento efímero, las fotos o la base de datos podrían desaparecer al reiniciar o desplegar. Usa siempre HTTPS. Después del despliegue, el hosting te dará una URL pública para compartir.

## Seguridad importante

- No subas secretos, `.env`, contraseñas ni la carpeta `data/` a un repositorio público.
- Usa contraseñas únicas, largas y diferentes para admin y novia.
- La app no registra ni envía contraseñas a servicios externos; la contraseña se comprueba en el servidor.
- La autenticación incluida es sencilla para un proyecto personal. Para datos especialmente sensibles o muchos usuarios, conviene añadir limitación de intentos, recuperación segura y almacenamiento de fotos con permisos privados.
- Máximo de carga configurado: 12 MB por petición. Formatos permitidos: JPG, JPEG, PNG, WEBP y GIF.
