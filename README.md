# Monitor de entrada F1 São Paulo 2026

Este proyecto revisa BuyTicket Brasil cada 5 minutos con GitHub Actions y notifica por Telegram y Gmail cuando **SETOR A / Inteira** aparece por **R$1.900 o menos** de precio base. No inicia la compra.

## Configuración en GitHub

1. Usa el repositorio público `Juanfa80/f1-ticket-monitor` que ya está creado. Los archivos del monitor quedan visibles; las credenciales solo se agregan como secretos.
2. En **Settings → Secrets and variables → Actions**, agrega estos secretos:
   - `TELEGRAM_BOT_TOKEN`: token del bot. Léelo del archivo local `telegram-config.json`; no lo pegues en el código ni en este chat.
   - `TELEGRAM_CHAT_ID`: `chat_id` del mismo archivo.
   - `GMAIL_USER`: la cuenta Gmail que enviará el aviso.
   - `GMAIL_APP_PASSWORD`: contraseña de aplicación de Google. No es la contraseña normal de Gmail.
   - `ALERT_EMAIL`: la dirección donde quieres recibir los avisos.
3. En **Settings → Actions → General → Workflow permissions**, habilita permiso de lectura y escritura para que el proceso pueda guardar el estado que evita alertas repetidas.
4. Ve a **Actions → Monitor F1 ticket → Run workflow** para hacer la primera ejecución manual. Revisa el log para confirmar que se seleccionaron las categorías correctas y se leyó el precio.

El workflow solo envía aviso si pudo seleccionar **SETOR A** y **Inteira** y leer el precio del botón de compra. Si la web cambia y el precio no se puede identificar, la ejecución falla sin mandar un aviso de precio.

## Límites y credenciales

GitHub Actions admite un intervalo programado mínimo de 5 minutos; la hora efectiva puede retrasarse cuando hay carga. En repositorios públicos, GitHub no cobra los runners estándar; los repositorios privados tienen una cuota mensual de minutos. El código deja de consultar después del 6 de noviembre de 2026; luego desactiva el workflow en la pestaña **Actions** para que no siga ejecutándose. Para Gmail, genera una contraseña de aplicación desde la seguridad de tu cuenta Google si la opción está habilitada y guárdala directamente como secreto de GitHub. Nunca la compartas por chat.

El estado de deduplicación queda en `state/last_alert.json` en el repositorio. El token de Telegram y las credenciales de Gmail no se guardan en los archivos del proyecto.
