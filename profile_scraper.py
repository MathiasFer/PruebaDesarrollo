# profile_scraper.py
import asyncio
import csv
import pandas as pd
from playwright.async_api import async_playwright
import time
import random


class ProfileScraper:
    """Clase para el scraping de conteos de seguidores usando Playwright."""

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self._closed = False

    async def _init_playwright(self):
        if self._closed:
            raise RuntimeError("El scraper ya fue cerrado y no puede reutilizarse")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self.page

    async def _login_instagram(self) -> bool:
        """Realiza el inicio de sesión en Instagram (LOGIN CORREGIDO)."""
        if not self.page:
            await self._init_playwright()

        print("Iniciando sesión en Instagram...")
        await self.page.goto("https://www.instagram.com/accounts/login/")
        await self.page.wait_for_timeout(5000)

        try:
            # Esperar inputs
            await self.page.wait_for_selector('input[name="username"]', timeout=10000)
            await self.page.wait_for_selector('input[name="password"]', timeout=10000)

            # Llenar credenciales
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)

            # 🔥 MÉTODO ESTABLE: ENTER (evita problemas con el botón)
            await self.page.keyboard.press("Enter")

            # Esperar navegación
            await self.page.wait_for_timeout(10000)

            # Verificar si sigue en login
            if "accounts/login" in self.page.url:
                print("❌ Login fallido (sigue en pantalla de login)")
                return False

            print("✅ Sesión iniciada exitosamente.")
            await self._handle_popups()
            return True

        except Exception as e:
            print(f"Error durante el login: {e}")
            return False

    async def _handle_popups(self):
        try:
            selectors = [
                "//button[contains(text(), 'Ahora no')]",
                "//button[contains(text(), 'Not Now')]"
            ]

            for selector in selectors:
                try:
                    await self.page.wait_for_selector(f'xpath={selector}', timeout=3000)
                    await self.page.click(f'xpath={selector}')
                    await self.page.wait_for_timeout(2000)
                except:
                    pass

        except Exception as e:
            print(f"No se pudieron cerrar pop-ups: {e}")

    def read_usernames_from_csv(self, filename: str) -> list[str]:
        usernames = []
        try:
            with open(filename, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)
                for row in reader:
                    if row:
                        usernames.append(row[0])
            print(f"Leídos {len(usernames)} usuarios de '{filename}'.")
            return usernames
        except Exception as e:
            print(f"Error al leer el CSV: {e}")
            return []

    async def _get_follower_count(self, username: str) -> str:
        try:
            await self.page.goto(f"https://www.instagram.com/{username}/")
            await self.page.wait_for_timeout(5000)

            followers_text = "NO_ENCONTRADO"

            try:
                elem = await self.page.query_selector(
                    'span[dir="auto"]:has-text("seguidores") span[title], '
                    'span[dir="auto"]:has-text("followers") span[title]'
                )
                if elem:
                    followers_text = await elem.get_attribute("title")
                    followers_text = followers_text.replace(",", "").replace(".", "").strip()
                    return followers_text
            except:
                pass

            page_text = await self.page.content()

            if "private" in page_text.lower():
                return "PRIVADA"
            if "Sorry" in page_text or "Lo sentimos" in page_text:
                return "NO_EXISTE"

            return followers_text

        except Exception as e:
            print(f"Error al procesar {username}: {e}")
            return "ERROR"

    def _save_results_to_csv(self, data: list[dict], filename: str):
        if not data:
            return
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=['username', 'followers_count'])
                writer.writeheader()
                writer.writerows(data)
            print(f"Resultados guardados en: {filename}")
        except Exception as e:
            print(f"Error al guardar el CSV: {e}")

    async def _scrape_follower_counts_async(self, usernames_list: list[str], output_csv: str):
        start_time = time.time()
        try:
            if not await self._login_instagram():
                return

            resultados = []
            for i, username in enumerate(usernames_list):
                print(f"\n[{i + 1}/{len(usernames_list)}] @{username}")
                await self.page.wait_for_timeout(random.randint(3000, 6000))
                count = await self._get_follower_count(username)
                resultados.append({'username': username, 'followers_count': count})
                print(f"{username} → {count}")

            self._save_results_to_csv(resultados, output_csv)

        finally:
            print(f"Tiempo total: {time.time() - start_time:.2f}s")
            await self._close_resources()

    async def _close_resources(self):
        try:
            if self.browser and not self._closed:
                await self.browser.close()
            if self.playwright and not self._closed:
                await self.playwright.stop()
            self._closed = True
        except:
            pass

    def scrape_follower_counts(self, usernames_list: list[str], output_csv: str):
        asyncio.run(self._scrape_follower_counts_async(usernames_list, output_csv))

    def close_driver(self):
        try:
            if not self._closed:
                asyncio.run(self._close_resources())
        except:
            pass
