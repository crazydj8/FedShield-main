from aggregator import Aggregator
from requesthandler import RequestHandler

agg_id = "1"


def get_updates(requesthandler: RequestHandler) -> list[dict[str, any]]:
    locality = "local"
    resp = requesthandler.retrieveModelUpdates(locality)
    
    return resp

def send_update(requesthandler: RequestHandler, global_update: dict[str, any]) -> None:
    locality = "global"
    
    requesthandler.storeModelUpdates(global_update, locality)

if __name__ == "__main__":
    requesthandler = RequestHandler(agg_id)
    state_dicts = get_updates(requesthandler)
    
    aggregator = Aggregator(agg_id)
    global_update = aggregator.aggregate(state_dicts)
    payload = aggregator.generateAndAttachProof()

    filename = 'global_update.pth'
    aggregator.save_model_locally(filename)
    send_update(requesthandler, payload)