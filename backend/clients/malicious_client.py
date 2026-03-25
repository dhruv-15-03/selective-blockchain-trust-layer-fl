from .client_base import FederatedClient

client = FederatedClient(
    client_id="malicious_client",
    account_index=4
)

client.register()

global_weights, round_number = client.get_global_model()

# Always dishonest: label flipping to simulate a compromised fraud model trainer.
label_flip_ratio = 0.8
local_weights = client.train(global_weights, round_number, label_flip_ratio=label_flip_ratio)
client.submit_update(local_weights, round_number)