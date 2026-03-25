import requests
import matplotlib.pyplot as plt

response = requests.get("http://127.0.0.1:8000/trust_history")
data = response.json()

for client, values in data.items():
    plt.plot(values, marker='o', label=client)

plt.xlabel("Round")
plt.ylabel("Trust Score")
plt.title("Trust Evolution Across Rounds")
plt.legend()
plt.grid(True)
plt.show()