from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

from bs4 import BeautifulSoup

import datetime
import requests
import urllib.parse


# =========================
# CONFIG — EDIT LOCALLY ONLY
# =========================
BOT_TOKEN = "7964413523:AAFxBhzCnLrQwWfhNjK5LTbcITMgqs_Yj4s"
CHAT_ID = "8229136722"
# =========================

URL = "https://concern.ir.rotterdam.nl/afspraak/maken/product/indienen-naturalisatieverzoek"


def should_run_now() -> bool:
    now = datetime.datetime.now().time()
    start = datetime.time(7, 46)
    end = datetime.time(22, 0)
    return start <= now < end


def send_telegram_message(message: str) -> None:
    encoded = urllib.parse.quote(message)
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage?chat_id={CHAT_ID}&text={encoded}"
    r = requests.get(url, timeout=20)
    if r.status_code != 200:
        raise RuntimeError(f"Telegram error {r.status_code}: {r.text}")


def main():
    checked_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if not should_run_now():
        print(f"Outside run window — skipping. {checked_at}")
        return

    from selenium.webdriver.chrome.options import Options

    chrome_options = Options()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)
    wait = WebDriverWait(driver, 30)

    try:
        driver.get(URL)

        # 0) Click on Verder button
        verder_button = wait.until(
            EC.element_to_be_clickable((By.NAME, "verder"))
        )
        verder_button.click()

        # 1) Find appointment option buttons (the list items)
        # Wait until either options appear or at least the body loads.
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "button.list-group-item-action")))

        option_buttons = driver.find_elements(By.CSS_SELECTOR, "button.list-group-item-action")
        option_buttons = [b for b in option_buttons if b.get_attribute("disabled") is None]

        if not option_buttons:
            # No options => nothing to do, and you don't want spam messages.
            print(f"No option buttons found. {checked_at}")
            return

        available = []
        for btn in option_buttons:
            try:
                p_text = btn.find_element(By.TAG_NAME, "p").text.strip().lower()
            except:
                p_text = ""
            if "wachtrij" not in p_text:
                available.append(btn)

        if not available:
            print(f"No appointments — only wachtrij. {checked_at}")
            return

        option_buttons = available

        # Build a readable list of options we saw (for the Telegram message if we do find an appointment)
        soup = BeautifulSoup(driver.page_source, "html.parser")
        option_html = soup.select("button.list-group-item-action")
        found_lines = []
        for b in option_html:
            if b.get("disabled") is None:
                h3 = b.find("h3")
                p = b.find("p")
                location = h3.get_text(strip=True) if h3 else "Unknown location"
                time_txt = p.get_text(" ", strip=True) if p else "Unknown time"
                found_lines.append(f"{location}: {time_txt}")

        # 2) Click the first available option
        option_buttons[0].click()

        # 3) After clicking, determine state:
        #    - Appointment available if "verder" button appears
        #    - No appointment if "Plaats in wachtrij" appears (wachtrij button)
        #
        # We wait for either button to become present/clickable.
        try:
            outcome = wait.until(
                EC.any_of(
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//button[contains(@class,'btn') and contains(@class,'btn-secondary') "
                            "and contains(@name,'in-focus:button') "
                            "and contains(translate(normalize-space(.),'VERDER','verder'),'verder')]"
                        )
                    ),
                    EC.presence_of_element_located(
                        (
                            By.XPATH,
                            "//button[contains(@class,'btn') and contains(@class,'btn-secondary') "
                            "and (contains(@name,'wachtrij') or contains(translate(normalize-space(.),'PLAATS IN WACHTRIJ','plaats in wachtrij'),'plaats in wachtrij'))]"
                        )
                    ),
                )
            )
        except TimeoutException:
            # Neither Verder nor Wachtrij appeared. Treat as unknown; no spam message.
            print(f"Clicked option, but neither 'verder' nor 'wachtrij' appeared. {checked_at}")
            return

        # Identify which button we got by inspecting its text/name
        text = (outcome.text or "").strip().lower()
        name = (outcome.get_attribute("name") or "").lower()

        if "verder" in text and "in-focus:button" in name:
            # Appointment available: click Verder (optional) and send message
            try:
                wait.until(EC.element_to_be_clickable(outcome)).click()
            except Exception:
                # Clicking isn't strictly required for notifying you
                pass

            msg = (
                f"Appointment available.\nChecked at: {checked_at}\n"
                "Options (first 10):\n" + "\n".join(found_lines[:10])
            )
            print(msg)
            send_telegram_message(msg)
            return

        # Wachtrij => explicitly no appointment
        if "wachtrij" in name or "plaats in wachtrij" in text:
            print(f"No appointment (wachtrij only). {checked_at}")
            return

        # Fallback: something else matched (unlikely)
        print(f"Unexpected state button: text='{outcome.text}' name='{outcome.get_attribute('name')}'. {checked_at}")
        return

    finally:
        driver.quit()


if __name__ == "__main__":
    main()

