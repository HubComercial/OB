from iqoptionapi.stable_api import IQ_Option

email = "Gutembergsouza875@gmail.com"
senha = "Souza280317@"

print("🔑 A testar login...")
api = IQ_Option(email, senha)
check, reason = api.connect()

if check:
    print("✅ Login bem-sucedido!")
else:
    print(f"❌ Falha: {reason}")
