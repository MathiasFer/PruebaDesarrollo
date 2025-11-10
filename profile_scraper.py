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
        # Inicializa las credenciales y las variables del navegador
        self.username = username
        self.password = password
        self.browser = None
        self.context = None
        self.page = None
        self.playwright = None
        self._closed = False  # Bandera para controlar si el navegador fue cerrado

    async def _init_playwright(self):
        """Inicializa Playwright, abre el navegador y una nueva pestaña."""
        if self._closed:
            raise RuntimeError("El scraper ya fue cerrado y no puede reutilizarse")

        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=False)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self.page

    async def _login_instagram(self) -> bool:
        """Realiza el inicio de sesión en Instagram."""
        if not self.page:
            await self._init_playwright()

        print("Iniciando sesión en Instagram...")
        await self.page.goto("https://www.instagram.com/accounts/login/")
        await self.page.wait_for_timeout(3000)

        try:
            # Completar los campos de usuario y contraseña
            await self.page.fill('input[name="username"]', self.username)
            await self.page.fill('input[name="password"]', self.password)

            # Hacer clic en el botón de inicio de sesión
            await self.page.click('button[type="submit"]')
            await self.page.wait_for_timeout(8000)

            # Verificar si el login fue exitoso
            current_url = self.page.url
            if "accounts/login" in current_url:
                print("Login fallido")
                return False

            print("Sesión iniciada exitosamente.")
            await self._handle_popups()
            return True

        except Exception as e:
            print(f"Error durante el login: {e}")
            return False

    async def _handle_popups(self):
        """Cierra los pop-ups que aparecen después del inicio de sesión."""
        try:
            # Pop-up "Guardar información"
            save_info_selectors = [
                "//button[contains(text(), 'Ahora no')]",
                "//button[contains(text(), 'Not Now')]"
            ]

            for selector in save_info_selectors:
                try:
                    await self.page.wait_for_selector(f'xpath={selector}', timeout=2000)
                    await self.page.click(f'xpath={selector}')
                    print("Pop-up 'Guardar información' cerrado.")
                    await self.page.wait_for_timeout(2000)
                    break
                except:
                    continue

            # Pop-up "Notificaciones"
            notification_selectors = [
                "//button[contains(text(), 'Ahora no')]",
                "//button[contains(text(), 'Not Now')]"
            ]

            for selector in notification_selectors:
                try:
                    await self.page.wait_for_selector(f'xpath={selector}', timeout=2000)
                    await self.page.click(f'xpath={selector}')
                    print("Pop-up 'Notificaciones' cerrado.")
                    await self.page.wait_for_timeout(2000)
                    break
                except:
                    continue

        except Exception as e:
            print(f"No se pudieron cerrar pop-ups: {e}")

    def read_usernames_from_csv(self, filename: str) -> list[str]:
        """Lee la lista de nombres de usuario desde un archivo CSV."""
        usernames = []
        try:
            with open(filename, mode='r', encoding='utf-8') as file:
                reader = csv.reader(file)
                next(reader)  # Saltar la cabecera
                for row in reader:
                    if row:
                        usernames.append(row[0])
            print(f"Leídos {len(usernames)} usuarios de '{filename}'.")
            return usernames
        except FileNotFoundError:
            print(f"Error: Archivo '{filename}' no encontrado.")
            return []
        except Exception as e:
            print(f"Error al leer el CSV: {e}")
            return []

    async def _get_follower_count(self, username: str) -> str:
        """Obtiene el número de seguidores de un usuario."""
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            await self.page.goto(profile_url)
            await self.page.wait_for_timeout(5000)

            followers_text = "NO_ENCONTRADO"

            # Estrategia 1: buscar el número en el atributo 'title'
            try:
                elem = await self.page.query_selector('span[dir="auto"]:has-text("seguidores") span[title]')
                if not elem:
                    elem = await self.page.query_selector('span[dir="auto"]:has-text("followers") span[title]')

                if elem:
                    followers_text = await elem.get_attribute("title") or await elem.inner_text()
                    followers_text = followers_text.replace(",", "").replace(".", "").strip()
                    return followers_text
            except:
                pass

            # Estrategia 2: buscar el texto que contenga "seguidores"
            try:
                span_es = await self.page.query_selector('span:has-text("seguidores")')
                if span_es:
                    text_content = await span_es.text_content()
                    if text_content:
                        import re
                        numbers = re.findall(r'[\d,\.]+', text_content)
                        if numbers:
                            followers_text = numbers[0].replace(",", "").replace(".", "").strip()
                            return followers_text
            except:
                pass

            # Estrategia 3: buscar el texto que contenga "followers"
            try:
                span_en = await self.page.query_selector('span:has-text("followers")')
                if span_en:
                    text_content = await span_en.text_content()
                    if text_content:
                        import re
                        numbers = re.findall(r'[\d,\.]+', text_content)
                        if numbers:
                            followers_text = numbers[0].replace(",", "").replace(".", "").strip()
                            return followers_text
            except:
                pass

            # Verificar si la cuenta es privada
            private_indicators = [
                "Esta cuenta es privada",
                "This account is private",
                "Cuenta privada",
                "Private account"
            ]

            page_text = await self.page.content()
            if any(indicator in page_text for indicator in private_indicators):
                return "PRIVADA"

            # Verificar si la cuenta no existe
            if "Lo sentimos" in page_text or "Sorry" in page_text or "no disponible" in page_text:
                return "NO_EXISTE"

            return followers_text

        except Exception as e:
            print(f"Error al procesar {username}: {e}")
            return "ERROR"

    def _save_results_to_csv(self, data: list[dict], filename: str):
        """Guarda los resultados del scraping en un archivo CSV."""
        if not data:
            return
        fieldnames = ['username', 'followers_count']
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(data)
            print(f"Resultados guardados en: {filename}")
        except Exception as e:
            print(f"Error al guardar el archivo CSV: {e}")

    async def _scrape_follower_counts_async(self, usernames_list: list[str], output_csv: str):
        """Ejecuta el proceso completo de scraping de forma asíncrona."""
        start_time = time.time()
        try:
            if not await self._login_instagram():
                return

            resultados = []
            print(f"Comenzando a escanear {len(usernames_list)} perfiles...")

            for i, username in enumerate(usernames_list):
                print(f"\n--- Procesando {i + 1}/{len(usernames_list)}: @{username} ---")

                # Espera aleatoria entre perfiles para evitar bloqueos
                await self.page.wait_for_timeout(random.randint(3000, 6000))

                count = await self._get_follower_count(username)
                resultados.append({'username': username, 'followers_count': count})
                print(f"{username} -> Seguidores: {count}")

            self._save_results_to_csv(resultados, output_csv)

        finally:
            # Mostrar tiempo total de ejecución
            end_time = time.time()
            duration = end_time - start_time
            print(f"Proceso finalizado a las {time.strftime('%H:%M:%S')} (Duración: {duration:.2f} segundos)")
            await self._close_resources()

    async def _close_resources(self):
        """Cierra todos los recursos de Playwright."""
        try:
            if self.browser and not self._closed:
                await self.browser.close()
                self.browser = None
            if self.playwright and not self._closed:
                await self.playwright.stop()
                self.playwright = None
            self._closed = True
        except Exception:
            pass

    def scrape_follower_counts(self, usernames_list: list[str], output_csv: str):
        """Método principal para ejecutar el scraping de forma síncrona."""
        asyncio.run(self._scrape_follower_counts_async(usernames_list, output_csv))

    def close_driver(self):
        """Cierra el navegador y los procesos de Playwright manualmente."""
        try:
            if not self._closed:
                asyncio.run(self._close_resources())
                print("Navegador del scraper cerrado correctamente.")
            else:
                print("El navegador ya estaba cerrado.")
        except Exception:
            print("El navegador ya se cerró automáticamente.")
