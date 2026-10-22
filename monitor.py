import json
import os
import re
import smtplib
import sys
from datetime import datetime
from email.message import EmailMessage
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright

URL = "https://buyticketbrasil.com/event/formula12026/session/8ca87908-1f59-48fc-a55f-45977cf01aa1?returnTo=%2Fsearch%3Fq%3Dformula%2B1"
TARGET_PRICE = 1900
STATE_FILE = Path("state/last_alert.json")


def brl_value(text: str) -> int | None:
    match = re.search(r"R$s*([d.]+)(?:,(d{2}))?", text, re.IGNORECASE)
    return int(match.group(1).replace(".", "")) if match else None


def select_option(page, combo_index: int, pattern: str) -> str:
    combos = page.get_by_role("combobox")
    if combos.count() <= combo_index:
        raise RuntimeError(f"No se encontró el selector {combo_index + 1}.")
    combo = combos.nth(combo_index)
    combo.click()
    page.get_by_role("option", name=re.compile(pattern, re.IGNORECASE)).click()
    return combo.inner_text().strip()


def check_ticket() -> tuple[int, str, str | None]:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page(locale="pt-BR", timezone_id="America/Sao_Paulo")
            page.goto(URL, wait_until="domcontentloaded", timeout=60_000)
            page.get_by_role("combobox").first.wait_for(state="visible", timeout=45_000)
            sector = select_option(page, 0, r"SETORs*A")
            page.get_by_role("combobox").nth(1).wait_for(state="visible", timeout=15_000)
            category = select_option(page, 1, r"Inteira")
            page.wait_for_timeout(1200)
            if not re.search(r"SETORs*A", sector, re.IGNORECASE) or not re.search(r"Inteira", category, re.IGNORECASE):
                raise RuntimeError("La página no confirmó SETOR A e Inteira después de seleccionarlos.")
            buttons = page.locator("button, [role='button']")
            purchase_text = None
            for i in range(buttons.count()):
                button = buttons.nth(i)
                label = button.inner_text().strip()
                if re.search(r"comprar", label, re.IGNORECASE) and brl_value(label) is not None:
                    purchase_text = label
                    break
                if re.search(r"comprar", label, re.IGNORECASE):
                    parent_text = button.evaluate("el => el.parentElement?.innerText || ''")
                    if brl_value(parent_text):
                        purchase_text = parent_text
                        break
            if not purchase_text:
                raise RuntimeError("No pude leer con certeza el precio del botón de compra.")
            price = brl_value(purchase_text)
            if price is None:
                raise RuntimeError("El precio visible no tiene un formato BRL reconocible.")
            fee_match = re.search(r"(?:taxa|comiss[aã]o|service fee)[^

]{0,80}(R$s*[d.]+(?:,d{2})?)", purchase_text, re.IGNORECASE)
            return price, purchase_text, fee_match.group(1) if fee_match else None
        finally:
            browser.close()


def read_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}


def save_state(state: dict) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "
", encoding="utf-8")


def alert_text(price: int, fee: str | None) -> str:
    local_time = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%d/%m/%Y %H:%M BRT")
    fee_text = f" Comisiones visibles: {fee}." if fee else " Comisiones no visibles en esta pantalla."
    formatted_price = f"{price:,}".replace(",", ".")
    return "F1 São Paulo 2026: SETOR A, Inteira disponible por R$" + formatted_price + " (precio base)." + fee_text + " Hora: " + local_time + ". Verifica el total antes de pagar.
" + URL


def send_telegram(message: str) -> None:
    import requests
    response = requests.post(
        f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/sendMessage",
        data={"chat_id": os.environ["TELEGRAM_CHAT_ID"], "text": message}, timeout=20)
    response.raise_for_status()
    if not response.json().get("ok"):
        raise RuntimeError("Telegram rechazó el envío.")


def send_gmail(subject: str, message: str) -> None:
    host = os.environ["GMAIL_USER"]
    email = EmailMessage()
    email["From"], email["To"], email["Subject"] = host, os.environ.get("ALERT_EMAIL", host), subject
    email.set_content(message)
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(host, os.environ["GMAIL_APP_PASSWORD"])
        smtp.send_message(email)


def main() -> int:
    if datetime.now(ZoneInfo("America/Sao_Paulo")).date() > datetime(2026, 11, 6).date():
        print("Seguimiento finalizado: fecha límite alcanzada.")
        return 0
    state = read_state()
    try:
        price, purchase_text, fee = check_ticket()
    except Exception as exc:
        print(f"REVIEW_FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print("SETOR A Inteira verificada: R$" + str(price) + "; texto de compra: " + purchase_text)
    if price > TARGET_PRICE:
        if state.get("last_alert_key"):
            state.update(last_alert_key=None, sent=[], last_checked=datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat())
            save_state(state)
        print("Sobre el límite; no se envían avisos.")
        return 0

    offer_key = f"setor-a-inteira:{price}"
    same_offer = state.get("last_alert_key") == offer_key
    sent = set(state.get("sent", [])) if same_offer else set()
    if same_offer and sent == {"telegram", "gmail"}:
        print("Oferta ya notificada; no se repite.")
        return 0
    old_price = state.get("last_alert_price")
    if state.get("last_alert_key") and not same_offer and old_price is not None and price >= old_price:
        print("Precio elegible ya notificado; no hay una baja adicional.")
        return 0

    message = alert_text(price, fee)
    failures = []
    channels = [
        ("telegram", bool(os.environ.get("TELEGRAM_BOT_TOKEN") and os.environ.get("TELEGRAM_CHAT_ID")), lambda: send_telegram(message)),
        ("gmail", bool(os.environ.get("GMAIL_USER") and os.environ.get("GMAIL_APP_PASSWORD")), lambda: send_gmail("F1: entrada Inteira sector A a R$1.900 o menos", message)),
    ]
    for name, ready, send in channels:
        if name in sent:
            continue
        if not ready:
            failures.append(name + ": faltan secretos")
            continue
        try:
            send()
            sent.add(name)
        except Exception as exc:
            failures.append(name + ": " + type(exc).__name__)

    state = state if same_offer else {"last_alert_key": offer_key, "last_alert_price": price, "sent": []}
    state["sent"] = sorted(sent)
    state["last_checked"] = datetime.now(ZoneInfo("America/Sao_Paulo")).isoformat()
    state["failures"] = failures
    save_state(state)
    print("Notificaciones enviadas: " + (", ".join(sorted(sent)) if sent else "ninguna"))
    if failures:
        print("Canales pendientes: " + "; ".join(failures), file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
