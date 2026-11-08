# NEXUS AI tomonidan avtomatik yaratilgan. Qo'lda o'zgartirmang.
import os, subprocess, sys, time

MODEL = "__MODEL__"
NGROK_DOMAIN = "__NGROK_DOMAIN__"
TUNNEL_USER = "__TUNNEL_USER__"

subprocess.run([sys.executable, "-m", "pip", "install", "-q", "pyngrok"], check=True)

from kaggle_secrets import UserSecretsClient
from pyngrok import ngrok

secrets = UserSecretsClient()

subprocess.run("apt-get install -y -q zstd && curl -fsSL https://ollama.com/install.sh | sh",
               shell=True, check=True)
subprocess.Popen(["ollama", "serve"],
                 env={**os.environ, "OLLAMA_HOST": "0.0.0.0:11434", "OLLAMA_ORIGINS": "*"})
time.sleep(8)

# Tunnel avval ochiladi, model yuklanayotganda ham backend holatni ko'ra oladi
ngrok.set_auth_token(secrets.get_secret("NGROK_TOKEN"))
password = secrets.get_secret("TUNNEL_PASSWORD")
tunnel = ngrok.connect(
    11434, "http",
    domain=NGROK_DOMAIN,
    basic_auth=[f"{TUNNEL_USER}:{password}"],
)
print("TUNNEL:", tunnel.public_url, flush=True)

subprocess.run(["ollama", "pull", MODEL], check=True)
print("MODEL READY:", MODEL, flush=True)

while True:
    time.sleep(60)
