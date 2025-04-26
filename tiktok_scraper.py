from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service  # Добавляем импорт Service
import time
import os

def get_user_videos(username, headless=True, max_videos=10, chrome_path=None):
    chrome_options = webdriver.ChromeOptions()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

    # Если указан пользовательский путь к Chrome, используем его
    if chrome_path:
        if not os.path.exists(chrome_path):
            raise FileNotFoundError(f"Указанный путь к Chrome не существует: {chrome_path}")
        service = Service(executable_path=chrome_path)
        driver = webdriver.Chrome(service=service, options=chrome_options)
    else:
        # Используем стандартное расположение Chrome
        driver = webdriver.Chrome(options=chrome_options)

    videos = []

    try:
        driver.get(f"https://www.tiktok.com/@{username}")
        time.sleep(2)

        retry_button_selector = "#main-content-others_homepage > div > div.css-833rgq-DivShareLayoutMain.e6y15914 > main > div > button"
        try:
            retry_button = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, retry_button_selector))
            )
            retry_button.click()
            print("Нажата кнопка 'Повторить'")
            time.sleep(2)
        except Exception as e:
            print(f"Кнопка 'Повторить' не найдена: {str(e)}")

        for _ in range(5):
            driver.execute_script("window.scrollBy(0, 2000);")
            time.sleep(2)

        WebDriverWait(driver, 15).until(
            EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-e2e='user-post-item']"))
        )

        video_elements = driver.find_elements(By.CSS_SELECTOR, "div[data-e2e='user-post-item'] a")
        videos = [elem.get_attribute("href") for elem in video_elements]
        print(f"Найдено {len(videos)} видео: {videos}")

        return videos[:max_videos]

    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return []
    finally:
        driver.quit()

if __name__ == "__main__":
    # Пример использования с пользовательским путем к Chrome
    custom_chrome_path = r'C:\Google\Chrome\Application\chrome.exe'  # Замените на ваш путь
    videos = get_user_videos("example_username", chrome_path=custom_chrome_path)
    print(f"Найденные видео: {videos}")