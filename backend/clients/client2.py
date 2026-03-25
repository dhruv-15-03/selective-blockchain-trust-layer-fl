from .client_base import FederatedClient
import numpy as np

# Create client using Ganache account[2]
client = FederatedClient(
    client_id="client_2",
    account_index=2
)

client.register()

# Get global model
global_weights, round_number = client.get_global_model()

# 🔥 Controlled alternating attack:
# Label-flip on EVEN rounds to simulate a dishonest participant.
if round_number % 2 == 0:
    print("⚠ client_2 label-flipping on this round")
    label_flip_ratio = 0.4
else:
    print("✅ client_2 behaving honestly this round")
    label_flip_ratio = 0.0

local_weights = client.train(global_weights, round_number, label_flip_ratio=label_flip_ratio)

# Submit update
response = client.submit_update(local_weights, round_number)

print(response)