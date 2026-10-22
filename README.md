# Monitor F1 São Paulo 2026

Consulta BuyTicket Brasil en GitHub Actions cada 5 minutos (puede haber retrasos del programador). Selecciona SETOR A e Inteira y avisa por Telegram cuando hay disponibilidad por R$1.900 o menos de precio base, comisiones aparte. No compra entradas.

Solo requiere los secretos TELEGRAM_BOT_TOKEN y TELEGRAM_CHAT_ID en Settings → Secrets and variables → Actions. No requiere Gmail ni contraseñas de correo. Nunca publiques el token.

Para comprobar el envío: Actions → Monitor F1 ticket → Run workflow → activa test_telegram. Para consultar el precio real, deja test_telegram desactivado. El modo de prueba no representa una oferta.

El navegador completo se ejecuta con Xvfb en el servidor. Los avisos repetidos se evitan guardando state/last_alert.json mediante un token del workflow con permiso contents: write.

El código deja de consultar después del 6 de noviembre de 2026. Desactiva el workflow después de esa fecha para detener las ejecuciones programadas.
