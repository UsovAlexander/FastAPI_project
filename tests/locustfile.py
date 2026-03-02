from locust import HttpUser, task, between
import random
import string

class URLShortenerUser(HttpUser):
    wait_time = between(1, 3)
    
    def on_start(self):
        """Регистрация и логин при старте"""
        self.username = f"user_{random.randint(1, 10000)}"
        self.password = "testpass123"

        self.client.post("/register", json={
            "email": f"{self.username}@example.com",
            "username": self.username,
            "password": self.password
        })

        response = self.client.post("/token", data={
            "username": self.username,
            "password": self.password
        })
        if response.status_code == 200:
            self.token = response.json()["access_token"]
            self.headers = {"Authorization": f"Bearer {self.token}"}
        else:
            self.token = None
            self.headers = {}
    
    @task(3)
    def create_short_link(self):
        """Создание короткой ссылки"""
        url = f"https://example.com/{random.randint(1, 1000000)}"
        self.client.post("/links/shorten", 
                        json={"original_url": url},
                        headers=self.headers)
    
    @task(2)
    def access_link(self):
        """Переход по короткой ссылке"""
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        self.client.get(f"/{short_code}", name="/[short_code]", allow_redirects=False)
    
    @task(1)
    def get_stats(self):
        """Получение статистики"""
        short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
        self.client.get(f"/links/{short_code}/stats", name="/links/[short_code]/stats")
    
    @task(1)
    def search_links(self):
        """Поиск ссылок"""
        url = f"https://example.com/{random.randint(1, 100)}"
        self.client.get(f"/links/search?original_url={url}", name="/links/search")
    
    @task(1)
    def update_link(self):
        """Обновление ссылки (только если есть токен)"""
        if self.token:
            short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            self.client.put(f"/links/{short_code}",
                          json={"original_url": "https://updated.com"},
                          headers=self.headers,
                          name="/links/[short_code]")
    
    @task(1)
    def delete_link(self):
        """Удаление ссылки (только если есть токен)"""
        if self.token:
            short_code = ''.join(random.choices(string.ascii_letters + string.digits, k=6))
            self.client.delete(f"/links/{short_code}",
                             headers=self.headers,
                             name="/links/[short_code]")