from .client_base import FederatedClient

client = FederatedClient(
    client_id="client_3",
    account_index=3
)

client.register()

global_weights, round_number = client.get_global_model()
local_weights = client.train(global_weights, round_number, label_flip_ratio=0.0)
client.submit_update(local_weights, round_number)