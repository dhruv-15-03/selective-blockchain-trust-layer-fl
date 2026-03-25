from .client_base import FederatedClient

# Create client using Ganache account[1]
client = FederatedClient(
    client_id="client_1",
    account_index=1
)

# Register once
client.register()

# FL Round
global_weights, round_number = client.get_global_model()
local_weights = client.train(global_weights, round_number, label_flip_ratio=0.0)
client.submit_update(local_weights, round_number)